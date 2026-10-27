"""VIXOR — Scan scheduling Celery tasks (T-041).

Re-verifies domain ownership before each scheduled scan run, then dispatches
a scan. Ownership re-verification is mandatory (LI-1, BO-10).
"""

from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger
from app.deps import get_session_factory
from app.models.domain import Domain, DomainStatus
from app.models.scan import Scan, ScanStatus
from app.models.scan_asset import ScanAsset
from app.workers.celery_app import celery_app
from app.workers.tasks_scan import run_scan

logger = get_logger("workers.schedule")


@celery_app.task(name="app.workers.tasks_schedule.run_scheduled_scan")  # type: ignore[untyped-decorator]
def run_scheduled_scan(domain_id: str) -> dict[str, Any]:
    """Run a scheduled scan for a domain after confirming ownership.

    Ownership must be current (verified within the re-verification window)
    before a scan is dispatched (LI-1, BO-10). If the domain is not currently
    verified, the scheduled run is skipped.
    """
    db = get_session_factory()()
    try:
        domain = db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            logger.error("domain_not_found_for_schedule", domain_id=domain_id)
            return {"domain_id": domain_id, "error": "domain not found"}

        # Ownership must be current before dispatching a scheduled scan.
        if domain.status != DomainStatus.verified or domain.verified_at is None:
            logger.warning(
                "scheduled_scan_skipped_domain_unverified",
                domain_id=domain_id,
                status=domain.status.value,
            )
            return {
                "domain_id": domain_id,
                "status": "skipped",
                "reason": "domain ownership not current",
            }

        now = datetime.now(UTC)
        # Record the scheduled run timestamp if the column exists.
        if hasattr(domain, "last_run_at"):
            domain.last_run_at = now
        db.commit()

        # Dispatch a scan for the domain's assets
        from app.models.asset import Asset

        assets = (
            db.query(Asset)
            .filter(Asset.domain_id == domain_id)
            .all()
        )
        asset_ids = [str(a.id) for a in assets]

        if not asset_ids:
            logger.warning("scheduled_scan_no_assets", domain_id=domain_id)
            return {
                "domain_id": domain_id,
                "status": "skipped",
                "reason": "no assets discovered",
            }

        scan = Scan(
            project_id=domain.project_id,
            domain_id=domain_id,
            triggered_by=None,
            status=ScanStatus.queued,
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)

        for asset_id in asset_ids:
            db.add(
                ScanAsset(scan_id=scan.id, asset_id=asset_id, status="pending")
            )
        db.commit()

        # Dispatch the async scan pipeline
        run_scan.delay(str(scan.id), domain_id, asset_ids)

        return {
            "domain_id": domain_id,
            "status": "dispatched",
            "scan_id": str(scan.id),
        }
    except Exception as exc:
        logger.exception("scheduled_scan_failed", domain_id=domain_id, error=str(exc))
        return {"domain_id": domain_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()
