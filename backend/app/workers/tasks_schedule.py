from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger
from app.deps import get_session_factory
from app.models.domain import Domain, DomainStatus
from app.models.scan import ScanStatus
from app.models.schedule import ScanSchedule
from app.services.cron_schedule import is_due, is_valid_cron
from app.services.scan_admission import ScanConcurrencyLimit, create_queued_scan
from app.workers.celery_app import celery_app
from app.workers.tasks_scan import run_scan

logger = get_logger("workers.schedule")


@celery_app.task(name="app.workers.tasks_schedule.run_scheduled_scan")  # type: ignore[untyped-decorator]
def run_scheduled_scan(domain_id: str) -> dict[str, Any]:
    """Revalidate domain ownership and dispatch a scan for in-scope assets."""
    db = get_session_factory()()
    try:
        domain = db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            return {"domain_id": domain_id, "status": "skipped", "reason": "domain not found"}
        if domain.status != DomainStatus.verified or domain.verified_at is None:
            return {"domain_id": domain_id, "status": "skipped", "reason": "domain ownership not current"}
        from app.models.asset import Asset, ScopeStatus
        assets = db.query(Asset).filter(
            Asset.domain_id == domain_id, Asset.scope_status == ScopeStatus.in_scope
        ).all()
        if not assets:
            return {"domain_id": domain_id, "status": "skipped", "reason": "no in-scope assets"}
        ids = [str(a.id) for a in assets]
        try:
            scan = create_queued_scan(
                db,
                project_id=domain.project_id,
                domain_id=domain_id,
                triggered_by=domain.project.owner_id,
                assets=assets,
            )
        except ScanConcurrencyLimit:
            db.rollback()
            return {"domain_id": domain_id, "status": "skipped", "reason": "project concurrency limit reached"}
        db.commit()
        try:
            run_scan.delay(str(scan.id), domain_id, ids)
        except Exception:
            scan.status = ScanStatus.failed
            scan.finished_at = datetime.now(UTC)
            scan.error_summary = "Scheduled scan task could not be dispatched."
            db.commit()
            raise
        return {"domain_id": domain_id, "status": "dispatched", "scan_id": str(scan.id)}
    except Exception as exc:
        db.rollback()
        logger.exception("scheduled_scan_failed", domain_id=domain_id, error=str(exc))
        return {"domain_id": domain_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks_schedule.dispatch_due_schedules")  # type: ignore[untyped-decorator]
def dispatch_due_schedules() -> dict[str, Any]:
    """Dispatch only schedules whose five-field cron expression is due."""
    db = get_session_factory()()
    try:
        now = datetime.now(UTC)
        schedules = db.query(ScanSchedule).filter(ScanSchedule.is_active.is_(True)).all()
        due: list[ScanSchedule] = []
        for schedule in schedules:
            try:
                if not is_valid_cron(schedule.cron):
                    logger.warning("invalid_scan_schedule_cron", schedule_id=schedule.id)
                    continue
                if is_due(schedule.cron, now, schedule.last_run_at):
                    due.append(schedule)
            except (ValueError, KeyError, TypeError):
                logger.warning("invalid_scan_schedule_cron", schedule_id=schedule.id)
        for schedule in due:
            run_scheduled_scan.delay(str(schedule.domain_id))
            schedule.last_run_at = now
        db.commit()
        return {"dispatched": len(due)}
    except Exception as exc:
        db.rollback()
        logger.exception("dispatch_due_schedules_failed", error=str(exc))
        return {"dispatched": 0, "error": str(exc)}
    finally:
        db.close()
