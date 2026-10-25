"""VIXOR — Findings API endpoints.

GET /findings/{id} - Get finding details (ownership-checked).
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.rbac import RequireViewer

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get(
    "/{finding_id}",
    response_model=dict,
    summary="Get finding details (ownership-checked)",
)
async def get_finding(
    finding_id: str,
    current_user: dict = Depends(RequireViewer),
):
    from app.deps import get_db as get_db_dep

    db = get_db_dep()

    from app.models.finding import Finding

    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        db.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found.",
        )

    # Ownership check through scan -> domain
    from app.models.scan import Scan

    scan = db.query(Scan).filter(Scan.id == finding.scan_id).first()
    if not scan:
        db.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found.",
        )

    from app.services.domain_service import DomainService

    domain_svc = DomainService(db)
    domain = domain_svc.get_domain(
        domain_id=scan.domain_id,
        user_id=current_user.get("user_id"),
        user_role=current_user.get("role", "viewer"),
    )
    db.close()

    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found.",
        )

    return {
        "id": finding.id,
        "asset_id": finding.asset_id,
        "scan_id": finding.scan_id,
        "fingerprint": finding.fingerprint,
        "source_tool": finding.source_tool.value,
        "title": finding.title,
        "description": finding.description,
        "severity_raw": finding.severity_raw,
        "cvss": finding.cvss,
        "cve_ids": finding.cve_ids,
        "evidence": finding.evidence,
        "remediation": finding.remediation,
        "created_at": finding.created_at.isoformat(),
    }
