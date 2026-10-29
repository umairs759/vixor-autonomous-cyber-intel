"""VIXOR — Reports API endpoints.

POST /scans/{id}/report - Generate PDF report (ownership-checked).
GET /reports/{id}/download - Download report (ownership-checked).
"""

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.core.rbac import require_role
from app.deps import get_db_session
from app.services.domain_service import DomainService
from app.services.report_service import ReportService

router = APIRouter(prefix="/scans", tags=["reports"])


@router.post(
    "/{scan_id}/report",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate PDF report (ownership-checked)",
)
async def generate_report(
    scan_id: str,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> dict[str, Any]:
    db = get_db_session()
    try:
        from app.models.scan import Scan

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

        service = ReportService(db)
        report = service.generate_report(scan_id)
        report.generated_by = current_user["user_id"]
        db.commit()
        db.refresh(report)

        return {
            "report_id": report.id,
            "scan_id": scan_id,
            "status": "generated",
            "file_path": report.file_path,
        }
    finally:
        db.close()


@router.get(
    "/reports/{report_id}/download",
    response_model=dict[str, Any],
    summary="Download PDF report (ownership-checked)",
)
async def download_report(
    report_id: str,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> dict[str, Any]:
    db = get_db_session()
    try:
        from app.models.report import Report
        from app.models.scan import Scan

        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found.",
            )

        # Ownership check through scan -> domain
        scan = db.query(Scan).filter(Scan.id == report.scan_id).first()
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found.",
            )

        domain_svc = DomainService(db)
        domain = domain_svc.get_domain(
            domain_id=scan.domain_id,
            user_id=current_user["user_id"],
            user_role=current_user.get("role", "viewer"),
        )
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
    finally:
        db.close()


@router.get(
    "/reports/{report_id}/file",
    summary="Download report PDF file (ownership-checked)",
)
async def download_report_file(
    report_id: str,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> FileResponse:
    db = get_db_session()
    try:
        from app.models.report import Report
        from app.models.scan import Scan

        report = db.query(Report).filter(Report.id == report_id).first()
        if not report or not report.file_path or not os.path.exists(report.file_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

        scan = db.query(Scan).filter(Scan.id == report.scan_id).first()
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

        domain_svc = DomainService(db)
        domain = domain_svc.get_domain(
            domain_id=scan.domain_id,
            user_id=current_user["user_id"],
            user_role=current_user.get("role", "viewer"),
        )
        if not domain:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

        return FileResponse(report.file_path, media_type="application/pdf", filename=f"{report_id}.pdf")
    finally:
        db.close()
