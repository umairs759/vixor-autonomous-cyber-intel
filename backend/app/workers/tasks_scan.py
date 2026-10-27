"""VIXOR — Scan pipeline Celery tasks (T-029, T-030, T-031).

Orchestrates scanning of assets: scope_guard -> scanner runners ->
normalization -> dedupe -> ML scoring -> regression -> correlation.
Progress is published via Redis pub/sub for the WebSocket dashboard.
"""

import json
from typing import Any

from app.core.logging import get_logger
from app.deps import get_session_factory
from app.models.scan import Scan, ScanStatus
from app.services.ml.features import extract_features
from app.services.ml.scoring import ScoringService
from app.services.scanning.orchestrator import ScanOrchestrator
from app.services.scope_guard import is_in_scope
from app.workers.celery_app import celery_app

logger = get_logger("workers.scan")
scoring_service = ScoringService()


def _publish_progress(scan_id: str, event: dict[str, Any]) -> None:
    """Publish a scan progress event to Redis pub/sub."""
    try:
        from app.redis import get_redis_client

        redis = get_redis_client()
        redis.publish(
            f"scan:{scan_id}",
            json.dumps({"scan_id": scan_id, **event}),
        )
    except Exception:
        logger.exception("progress_publish_failed", scan_id=scan_id)


@celery_app.task(bind=True, name="app.workers.tasks_scan.run_scan")  # type: ignore[untyped-decorator]
def run_scan(  # type: ignore[no-untyped-def]
    self, scan_id: str, domain_id: str, asset_ids: list[str]
) -> dict[str, Any]:
    """Run the full scan pipeline for a scan.

    Enforces scope_guard on every asset before dispatching scanners.
    Publishes progress events to Redis for live dashboard updates.
    """
    db = get_session_factory()()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            logger.error("scan_not_found", scan_id=scan_id)
            return {"scan_id": scan_id, "error": "scan not found"}

        scan.status = ScanStatus.running
        db.commit()

        from app.models.domain import Domain

        domain = db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            scan.status = ScanStatus.failed
            scan.error_summary = "domain not found"
            db.commit()
            return {"scan_id": scan_id, "error": "domain not found"}

        orchestrator = ScanOrchestrator(timeout_seconds=1800)
        all_findings: list[dict[str, Any]] = []

        for asset_id in asset_ids:
            from app.models.asset import Asset

            asset = db.query(Asset).filter(Asset.id == asset_id).first()
            if not asset:
                continue

            # scope_guard enforcement before touching the target
            domain_verified = (
                domain.status == "verified" and domain.verified_at is not None
            )
            in_scope, reason = is_in_scope(
                domain, asset.hostname, resolve_dns=False
            )
            if not in_scope:
                logger.warning(
                    "asset_out_of_scope",
                    scan_id=scan_id,
                    asset_id=asset_id,
                    hostname=asset.hostname,
                    reason=reason,
                )
                continue

            result = orchestrator.scan_asset(
                domain_root=domain.root_domain,
                hostname=asset.hostname,
                domain_verified=domain_verified,
                verified_at=domain.verified_at,
            )

            for finding in result.get("findings", []):
                # ML scoring + SHAP explanation
                features = extract_features(finding)
                score_result = scoring_service.score(features)

                from app.models.finding import Finding
                from app.models.finding_score import FindingScore

                db_finding = Finding(
                    asset_id=asset_id,
                    scan_id=scan_id,
                    fingerprint=finding.get("fingerprint", ""),
                    source_tool=finding.get("source_tool", "unknown"),
                    title=finding.get("title", ""),
                    description=finding.get("description", ""),
                    severity_raw=finding.get("severity_raw", "info"),
                    cvss=finding.get("cvss"),
                    cve_ids=finding.get("cve_ids", []),
                    evidence=finding.get("evidence", {}),
                    remediation=finding.get("remediation", ""),
                )
                db.add(db_finding)
                db.flush()

                fs = FindingScore(
                    finding_id=db_finding.id,
                    risk_score=score_result.get("risk_score", 0.0),
                    risk_class=score_result.get("risk_class", "low"),
                    model_version=score_result.get("model_version", "fallback"),
                    features=score_result.get("features", {}),
                    shap_values=score_result.get("shap_values", {}),
                    narrative=score_result.get("narrative", ""),
                    scored_by=score_result.get("scored_by", "fallback"),
                )
                db.add(fs)
                all_findings.append(
                    {
                        "finding_id": db_finding.id,
                        "fingerprint": finding.get("fingerprint", ""),
                        "risk_score": score_result.get("risk_score", 0.0),
                        "narrative": score_result.get("narrative", ""),
                    }
                )

        db.commit()
        scan.status = ScanStatus.completed
        db.commit()

        _publish_progress(
            scan_id,
            {"status": "completed", "findings": len(all_findings)},
        )
        return {
            "scan_id": scan_id,
            "status": "completed",
            "findings": all_findings,
        }
    except Exception as exc:
        logger.exception("scan_failed", scan_id=scan_id, error=str(exc))
        try:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if scan:
                scan.status = ScanStatus.failed
                scan.error_summary = str(exc)[:500]
                db.commit()
        except Exception as exc2:
            logger.exception("scan_db_update_failed", scan_id=scan_id, error=str(exc2))
        return {"scan_id": scan_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()
