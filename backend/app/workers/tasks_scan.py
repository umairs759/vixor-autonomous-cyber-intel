"""Celery scan pipeline with scope checks, scoring, history, and correlation."""

import json
from datetime import UTC, datetime
from typing import Any

from app.config import get_settings
from app.core.logging import get_logger
from app.deps import get_session_factory
from app.models.scan import Scan, ScanStatus
from app.models.scan_asset import ScanAsset
from app.services.correlation_engine import CorrelationEngine
from app.services.ml.features import extract_features
from app.services.ml.scoring import ScoringService
from app.services.regression_engine import RegressionEngine
from app.services.scanning.normalizer import dedupe_findings
from app.services.scanning.orchestrator import ScanOrchestrator
from app.services.scope_guard import is_in_scope
from app.workers.celery_app import celery_app

logger = get_logger("workers.scan")
scoring_service = ScoringService()


def _publish_progress(scan_id: str, event: dict[str, Any]) -> None:
    """Publish a scan progress event to Redis pub/sub."""
    try:
        from app.redis import get_redis_client

        redis_client = get_redis_client()
        redis_client.publish(
            f"scan:{scan_id}",
            json.dumps({"scan_id": scan_id, **event}),
        )
    except Exception:
        logger.exception("progress_publish_failed", scan_id=scan_id)


@celery_app.task(bind=True, name="app.workers.tasks_scan.run_scan")  # type: ignore[untyped-decorator]
def run_scan(  # type: ignore[no-untyped-def]
    self, scan_id: str, domain_id: str, asset_ids: list[str]
) -> dict[str, Any]:
    """Execute a queued scan once and persist its complete intelligence."""
    from app.models.asset import Asset, ScopeStatus
    from app.models.correlation import Correlation
    from app.models.domain import Domain, DomainStatus
    from app.models.finding import Finding
    from app.models.finding_score import FindingScore
    from app.services.scanning.zap_runner import ZapRunner

    db = get_session_factory()()
    try:
        now = datetime.now(UTC)
        claimed = (
            db.query(Scan)
            .filter(Scan.id == scan_id, Scan.status == ScanStatus.queued)
            .update(
                {Scan.status: ScanStatus.running, Scan.started_at: now},
                synchronize_session=False,
            )
        )
        db.commit()
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan is None:
            logger.error("scan_not_found", scan_id=scan_id)
            return {"scan_id": scan_id, "status": "not_found"}
        if not claimed:
            return {"scan_id": scan_id, "status": scan.status.value, "duplicate": True}

        _publish_progress(scan_id, {"status": "running", "completed_assets": 0})
        domain = db.query(Domain).filter(Domain.id == domain_id).first()
        if (
            domain is None
            or scan.domain_id != domain_id
            or scan.project_id != domain.project_id
            or domain.status != DomainStatus.verified
            or domain.verified_at is None
        ):
            scan.status = ScanStatus.failed
            scan.finished_at = datetime.now(UTC)
            scan.error_summary = "Domain ownership is missing, stale, or mismatched."
            db.commit()
            return {"scan_id": scan_id, "status": "failed", "error": scan.error_summary}

        requested_ids = list(dict.fromkeys(asset_ids))
        assets = (
            db.query(Asset)
            .filter(Asset.id.in_(requested_ids), Asset.domain_id == domain.id)
            .all()
            if requested_ids
            else []
        )
        if len(assets) != len(requested_ids) or not assets:
            scan.status = ScanStatus.failed
            scan.finished_at = datetime.now(UTC)
            scan.error_summary = (
                "Scan assets are missing or do not belong to the domain."
            )
            db.commit()
            return {"scan_id": scan_id, "status": "failed", "error": scan.error_summary}

        zap_runner = ZapRunner(
            zap_url=get_settings().ZAP_API_URL,
            api_key=get_settings().ZAP_API_KEY,
            timeout_seconds=get_settings().SCAN_TOOL_TIMEOUT_SECONDS,
        )
        orchestrator = ScanOrchestrator(
            zap_runner=zap_runner,
            timeout_seconds=get_settings().SCAN_TOOL_TIMEOUT_SECONDS,
        )
        all_findings: list[dict[str, Any]] = []
        scanner_errors: list[str] = []
        scanned_count = 0

        for index, asset in enumerate(assets, start=1):
            scan_asset = (
                db.query(ScanAsset)
                .filter(ScanAsset.scan_id == scan_id, ScanAsset.asset_id == asset.id)
                .first()
            )
            if scan_asset is None:
                scanner_errors.append(f"Missing scan association for asset {asset.id}")
                continue
            if asset.scope_status != ScopeStatus.in_scope:
                scan_asset.status = "skipped"
                scanner_errors.append(f"Asset {asset.hostname} is outside stored scope")
                db.commit()
                continue

            in_scope, reason = is_in_scope(domain, asset.hostname, resolve_dns=True)
            if not in_scope:
                scan_asset.status = "skipped"
                scanner_errors.append(
                    reason or f"Asset {asset.hostname} is outside scope"
                )
                db.commit()
                continue

            scan_asset.status = "running"
            db.commit()
            _publish_progress(
                scan_id,
                {
                    "status": "running",
                    "completed_assets": index - 1,
                    "total_assets": len(assets),
                    "current_asset": asset.hostname,
                },
            )
            result = orchestrator.scan_asset(
                domain_root=domain.root_domain,
                hostname=asset.hostname,
                domain_verified=True,
                verified_at=domain.verified_at,
            )
            scanned_count += 1
            asset_findings, duplicate_fingerprints = dedupe_findings(
                result.get("findings", []), db, scan_id=scan_id, asset_id=asset.id
            )
            unique_findings: list[dict[str, Any]] = []
            seen_fingerprints: set[str] = set()
            for finding_data in asset_findings:
                fingerprint = str(finding_data.get("fingerprint", ""))
                if not fingerprint or fingerprint in seen_fingerprints:
                    continue
                seen_fingerprints.add(fingerprint)
                unique_findings.append(finding_data)

            for finding_data in unique_findings:
                feature_values = extract_features(finding_data)
                score_result = scoring_service.score(feature_values)
                finding = Finding(
                    asset_id=asset.id,
                    scan_id=scan_id,
                    fingerprint=str(finding_data["fingerprint"]),
                    source_tool=finding_data.get("source_tool", "nuclei"),
                    title=finding_data.get("title", "Untitled finding"),
                    description=finding_data.get("description", ""),
                    severity_raw=finding_data.get("severity_raw", "info"),
                    cvss=finding_data.get("cvss"),
                    cve_ids=finding_data.get("cve_ids", []),
                    evidence=finding_data.get("evidence", {}),
                    remediation=finding_data.get("remediation", ""),
                )
                db.add(finding)
                db.flush()
                db.add(
                    FindingScore(
                        finding_id=finding.id,
                        risk_score=score_result.get("risk_score", 0.0),
                        risk_class=score_result.get("risk_class", "low"),
                        model_version=score_result.get("model_version", "fallback"),
                        features=score_result.get("features", {}),
                        shap_values=score_result.get("shap_values", {}),
                        narrative=score_result.get("narrative", ""),
                        scored_by=score_result.get("scored_by", "fallback"),
                    )
                )
                all_findings.append(
                    {
                        "finding_id": finding.id,
                        "fingerprint": finding.fingerprint,
                        "risk_score": score_result.get("risk_score", 0.0),
                    }
                )

            scan_asset.status = result.get("status", "completed")
            scanner_errors.extend(result.get("errors", []))
            if duplicate_fingerprints:
                logger.info(
                    "scan_findings_deduplicated",
                    scan_id=scan_id,
                    asset_id=asset.id,
                    count=len(duplicate_fingerprints),
                )
            db.commit()
            _publish_progress(
                scan_id,
                {
                    "status": "running",
                    "completed_assets": index,
                    "total_assets": len(assets),
                    "findings": len(all_findings),
                },
            )

        previous_scan = (
            db.query(Scan)
            .filter(
                Scan.domain_id == domain_id,
                Scan.id != scan_id,
                Scan.status == ScanStatus.completed,
            )
            .order_by(Scan.created_at.desc())
            .first()
        )
        RegressionEngine(db).classify_scan_findings(
            scan_id,
            previous_scan_id=str(previous_scan.id) if previous_scan else None,
        )

        correlations = 0
        correlation_engine = CorrelationEngine(db)
        for asset in assets:
            for correlation_data in correlation_engine.correlate_findings(
                scan_id, str(asset.id)
            ):
                existing = (
                    db.query(Correlation)
                    .filter(
                        Correlation.scan_id == scan_id,
                        Correlation.asset_id == asset.id,
                        Correlation.title == correlation_data["title"],
                    )
                    .first()
                )
                if existing:
                    continue
                db.add(Correlation(**correlation_data))
                correlations += 1

        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        scan.finished_at = datetime.now(UTC)
        if scanned_count == 0 or (scanner_errors and not all_findings):
            scan.status = ScanStatus.failed
        elif scanner_errors:
            scan.status = ScanStatus.partial
        else:
            scan.status = ScanStatus.completed
        scan.error_summary = "; ".join(scanner_errors)[:500] or None
        db.commit()

        final_status = scan.status.value
        _publish_progress(
            scan_id,
            {
                "status": final_status,
                "findings": len(all_findings),
                "correlations": correlations,
                "error": scan.error_summary,
            },
        )
        return {
            "scan_id": scan_id,
            "status": final_status,
            "findings": all_findings,
            "correlations": correlations,
        }
    except Exception as exc:
        logger.exception("scan_failed", scan_id=scan_id, error=str(exc))
        db.rollback()
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan:
            scan.status = ScanStatus.failed
            scan.finished_at = datetime.now(UTC)
            scan.error_summary = str(exc)[:500]
            db.commit()
        return {"scan_id": scan_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()
