"""VIXOR — Scans API endpoints.

POST /scans - Start a scan (ownership-checked).
GET /scans/{id} - Get scan details (ownership-checked).
GET /scans/{id}/findings - Get scan findings (ownership-checked).
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.rbac import require_role
from app.deps import get_db, get_db_session
from app.models.asset import Asset, ScopeStatus
from app.models.domain import DomainStatus
from app.models.scan import Scan, ScanStatus
from app.schemas.scan import ScanCreateRequest
from app.services.domain_service import DomainService
from app.services.scan_admission import ScanConcurrencyLimit, create_queued_scan
from app.services.scope_guard import is_in_scope

router = APIRouter(prefix="/scans", tags=["scans"])


def get_domain_service(db: Session = Depends(get_db)) -> DomainService:
    return DomainService(db=db)


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a scan (ownership-checked)",
)
async def create_scan(
    scan_data: ScanCreateRequest,
    db: Session = Depends(get_db),
    domain_svc: DomainService = Depends(get_domain_service),
    current_user: dict[str, Any] = Depends(require_role("analyst")),
) -> dict[str, Any]:
    domain = domain_svc.get_domain(
        domain_id=scan_data.domain_id,
        user_id=current_user["user_id"],
        user_role=current_user.get("role", "viewer"),
    )
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found.",
        )
    if domain.status != DomainStatus.verified or domain.verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Domain ownership must be verified before scanning.",
        )

    requested_ids = set(scan_data.asset_ids)
    asset_query = db.query(Asset).filter(Asset.domain_id == domain.id)
    if requested_ids:
        asset_query = asset_query.filter(Asset.id.in_(requested_ids))
    else:
        asset_query = asset_query.filter(Asset.scope_status == ScopeStatus.in_scope)
    assets = asset_query.all()
    if requested_ids and len(assets) != len(requested_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more assets do not belong to this domain.",
        )
    if not assets:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No in-scope assets are available for this domain.",
        )

    for asset in assets:
        if asset.scope_status != ScopeStatus.in_scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="An asset is outside the approved scan scope.",
            )
        in_scope, reason = is_in_scope(domain, asset.hostname, resolve_dns=True)
        if not in_scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=reason or "Asset is outside the approved scan scope.",
            )

    try:
        scan = create_queued_scan(
            db,
            project_id=domain.project_id,
            domain_id=domain.id,
            triggered_by=current_user["user_id"],
            assets=assets,
        )
        db.commit()
        db.refresh(scan)
    except ScanConcurrencyLimit as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    try:
        from app.workers.tasks_scan import run_scan

        run_scan.delay(
            str(scan.id), str(domain.id), [str(asset.id) for asset in assets]
        )
    except Exception as exc:
        scan.status = ScanStatus.failed
        scan.error_summary = "Scan task could not be dispatched."
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scan task queue is unavailable.",
        ) from exc

    return {"scan_id": scan.id, "status": scan.status.value}


@router.post("/{scan_id}/cancel", summary="Cancel a queued scan")
async def cancel_scan(
    scan_id: str,
    db: Session = Depends(get_db),
    current_user: dict[str, Any] = Depends(require_role("analyst")),
) -> dict[str, Any]:
    from app.models.project import Project

    scan = (
        db.query(Scan)
        .join(Project, Scan.project_id == Project.id)
        .filter(Scan.id == scan_id)
        .with_for_update()
        .first()
    )
    if scan is None or (
        current_user.get("role") != "admin"
        and scan.project.owner_id != current_user["user_id"]
    ):
        raise HTTPException(status_code=404, detail="Scan not found.")
    if scan.status != ScanStatus.queued:
        raise HTTPException(status_code=409, detail="Only queued scans can be cancelled.")
    scan.status = ScanStatus.cancelled
    scan.finished_at = datetime.now(UTC)
    scan.error_summary = "Cancelled before execution."
    db.commit()
    return {"scan_id": scan.id, "status": scan.status.value}


@router.get(
    "",
    response_model=list[dict[str, Any]],
    summary="List scans (ownership-filtered)",
)
async def list_scans(
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> list[dict[str, Any]]:
    db = get_db_session()
    try:
        from app.models.project import Project

        user_id = current_user["user_id"]
        user_role = current_user.get("role", "viewer")

        if user_role == "admin":
            scans = db.query(Scan).all()
        else:
            scans = (
                db.query(Scan)
                .join(Project, Scan.project_id == Project.id)
                .filter(Project.owner_id == user_id)
                .all()
            )

        return [
            {
                "id": s.id,
                "project_id": s.project_id,
                "domain_id": s.domain_id,
                "status": s.status.value,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "finished_at": s.finished_at.isoformat() if s.finished_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in scans
        ]
    finally:
        db.close()


@router.get(
    "/{scan_id}",
    response_model=dict,
    summary="Get scan details (ownership-checked)",
)
async def get_scan(
    scan_id: str,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> dict[str, Any]:
    db = get_db_session()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found.",
            )

        # Ownership check
        domain_svc = DomainService(db)
        domain = domain_svc.get_domain(
            domain_id=scan.domain_id,
            user_id=current_user["user_id"],
            user_role=current_user.get("role", "viewer"),
        )

        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found.",
            )

        return {
            "id": scan.id,
            "project_id": scan.project_id,
            "domain_id": scan.domain_id,
            "status": scan.status.value,
            "started_at": scan.started_at.isoformat() if scan.started_at else None,
            "finished_at": scan.finished_at.isoformat() if scan.finished_at else None,
            "error_summary": scan.error_summary,
        }
    finally:
        db.close()


@router.get(
    "/{scan_id}/findings",
    response_model=list[dict[str, Any]],
    summary="Get scan findings (ownership-checked)",
)
async def get_scan_findings(
    scan_id: str,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> list[dict[str, Any]]:
    db = get_db_session()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found.",
            )

        # Ownership check
        domain_svc = DomainService(db)
        domain = domain_svc.get_domain(
            domain_id=scan.domain_id,
            user_id=current_user["user_id"],
            user_role=current_user.get("role", "viewer"),
        )
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found.",
            )

        from app.models.finding import Finding

        findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()

        return [
            {
                "id": f.id,
                "asset_id": f.asset_id,
                "fingerprint": f.fingerprint,
                "source_tool": f.source_tool.value,
                "title": f.title,
                "description": f.description,
                "severity_raw": f.severity_raw,
                "cvss": f.cvss,
                "cve_ids": f.cve_ids,
                "evidence": f.evidence,
                "remediation": f.remediation,
                "created_at": f.created_at.isoformat(),
            }
            for f in findings
        ]
    finally:
        db.close()
