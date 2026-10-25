"""VIXOR — Scans API endpoints.

POST /scans - Start a scan (ownership-checked).
GET /scans/{id} - Get scan details (ownership-checked).
GET /scans/{id}/findings - Get scan findings (ownership-checked).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.rbac import RequireAnalyst, RequireViewer
from app.deps import get_db
from app.models.scan import Scan, ScanStatus
from app.services.domain_service import DomainService

router = APIRouter(prefix="/scans", tags=["scans"])


def get_domain_service(db: Session = Depends(get_db)) -> DomainService:
    return DomainService(db=db)


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a scan (ownership-checked)",
)
async def create_scan(
    domain_id: str,
    asset_ids: list[str],
    domain_svc: DomainService = Depends(get_domain_service),
    current_user: dict = Depends(RequireAnalyst),
):
    domain = domain_svc.get_domain(
        domain_id=domain_id,
        user_id=current_user.get("user_id"),
        user_role=current_user.get("role", "viewer"),
    )
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found.",
        )

    from app.deps import get_db as get_db_dep

    db = get_db_dep()

    scan = Scan(
        project_id=domain.project_id,
        domain_id=domain_id,
        triggered_by=current_user.get("user_id"),
        status=ScanStatus.queued,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Create scan_assets
    from app.models.scan_asset import ScanAsset

    for asset_id in asset_ids:
        sa = ScanAsset(scan_id=scan.id, asset_id=asset_id, status="pending")
        db.add(sa)
    db.commit()
    db.close()

    return {"scan_id": scan.id, "status": scan.status.value}


@router.get(
    "/{scan_id}",
    response_model=dict,
    summary="Get scan details (ownership-checked)",
)
async def get_scan(
    scan_id: str,
    current_user: dict = Depends(RequireViewer),
):
    from app.deps import get_db as get_db_dep

    db = get_db_dep()

    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    db.close()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found.",
        )

    # Ownership check
    from app.services.domain_service import DomainService

    domain_svc = DomainService(get_db_dep())
    domain = domain_svc.get_domain(
        domain_id=scan.domain_id,
        user_id=current_user.get("user_id"),
        user_role=current_user.get("role", "viewer"),
    )
    get_db_dep().close()

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


@router.get(
    "/{scan_id}/findings",
    response_model=list[dict],
    summary="Get scan findings (ownership-checked)",
)
async def get_scan_findings(
    scan_id: str,
    current_user: dict = Depends(RequireViewer),
):
    from app.deps import get_db as get_db_dep

    db = get_db_dep()

    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        db.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found.",
        )

    # Ownership check
    from app.services.domain_service import DomainService

    domain_svc = DomainService(db)
    domain = domain_svc.get_domain(
        domain_id=scan.domain_id,
        user_id=current_user.get("user_id"),
        user_role=current_user.get("role", "viewer"),
    )
    if not domain:
        db.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found.",
        )

    from app.models.finding import Finding

    findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()
    db.close()

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
