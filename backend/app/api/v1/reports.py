"""VIXOR — Reports API endpoints.

POST /scans/{id}/report - Generate PDF report (ownership-checked).
GET /reports/{id}/download - Download report (ownership-checked).
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.rbac import RequireViewer

router = APIRouter(prefix="/scans", tags=["reports"])


@router.post(
    "/{scan_id}/report",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate PDF report (ownership-checked)",
)
async def generate_report(
    scan_id: str,
    current_user: dict = Depends(RequireViewer),
):
    from app.deps import get_db as get_db_dep

    db = get_db_dep()

    from app.models.scan import Scan

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
    db.close()

    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found.",
        )

    from app.models.report import Report

    report = Report(
        scan_id=scan_id,
        generated_by=current_user.get("user_id"),
        file_path=f"/reports/{scan_id}.pdf",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    db.close()

    return {
        "report_id": report.id,
        "scan_id": scan_id,
        "status": "generated",
    }


@router.get(
    "/reports/{report_id}/download",
    response_model=dict,
    summary="Download PDF report (ownership-checked)",
)
async def download_report(
    report_id: str,
    current_user: dict = Depends(RequireViewer),
):
    from app.deps import get_db as get_db_dep

    db = get_db_dep()

    from app.models.report import Report

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        db.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    # Ownership check through scan -> domain
    from app.models.scan import Scan

    scan = db.query(Scan).filter(Scan.id == report.scan_id).first()
    if not scan:
        db.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
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
            detail="Report not found.",
        )

    return {
        "report_id": report.id,
        "file_path": report.file_path,
        "download_url": f"/api/v1/scans/reports/{report.id}/file",
    }
