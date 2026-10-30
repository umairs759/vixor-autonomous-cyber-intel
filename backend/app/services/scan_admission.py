from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.project import Project
from app.models.scan import Scan, ScanStatus
from app.models.scan_asset import ScanAsset


class ScanConcurrencyLimit(Exception):
    """Raised when a project already has its configured number of scans."""


def create_queued_scan(
    db: Session,
    *,
    project_id: str,
    domain_id: str,
    triggered_by: str,
    assets: list[Any],
) -> Scan:
    """Atomically reserve one project scan slot and create its scan rows.

    PostgreSQL serializes admission on the project row. SQLite's no-op UPDATE
    takes a database write reservation, preserving the same invariant in tests.
    Queued and running scans both hold slots. Abandoned scans are marked failed
    after 24 hours so a crashed worker cannot hold capacity indefinitely.
    """
    project_query = db.query(Project).filter(Project.id == project_id).with_for_update()
    project = project_query.first()
    if project is None:
        raise ValueError("Project not found")
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        db.execute(
            update(Project).where(Project.id == project_id).values(name=Project.name)
        )

    now = datetime.now(UTC)
    stale_cutoff = now - timedelta(hours=24)
    stale = (
        db.query(Scan)
        .filter(
            Scan.project_id == project_id,
            Scan.status.in_([ScanStatus.queued, ScanStatus.running]),
            func.coalesce(Scan.started_at, Scan.created_at) < stale_cutoff,
        )
        .all()
    )
    for old_scan in stale:
        old_scan.status = ScanStatus.failed
        old_scan.finished_at = now
        old_scan.error_summary = "Scan expired after worker lease timeout."

    active_count = (
        db.query(func.count(Scan.id))
        .filter(
            Scan.project_id == project_id,
            Scan.status.in_([ScanStatus.queued, ScanStatus.running]),
        )
        .scalar()
        or 0
    )
    limit = get_settings().MAX_CONCURRENT_SCANS_PER_PROJECT
    if active_count >= limit:
        raise ScanConcurrencyLimit(
            f"Project scan limit reached ({limit} active scans)."
        )

    scan = Scan(
        project_id=project_id,
        domain_id=domain_id,
        triggered_by=triggered_by,
        status=ScanStatus.queued,
    )
    db.add(scan)
    db.flush()
    for asset in assets:
        db.add(ScanAsset(scan_id=scan.id, asset_id=asset.id, status="pending"))
    return scan
