"""VIXOR — Reports API endpoints.

POST /scans/{id}/report - Generate PDF report (ownership-checked).
GET /reports/{id}/download - Download report (ownership-checked).
"""

import asyncio
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.core.rbac import require_role
from app.deps import get_db_session
from app.services.domain_service import DomainService
from app.services.report_service import ReportService

router = APIRouter(prefix="/scans", tags=["reports"])


def _read_pdf_header(path: str) -> bytes:
    with open(path, "rb") as pdf_file:
        return pdf_file.read(5)


@router.post(
    "/{scan_id}/report",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate PDF report (ownership-checked)",
)
async def generate_report(
    scan_id: str,
    current_user: dict[str, Any] = Depends(require_role("analyst")),
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
        report = service.generate_report(
            scan_id, generated_by=current_user["user_id"]
        )

        return {
            "report_id": report.id,
            "scan_id": scan_id,
            "status": "generated",
        }
    finally:
        db.close()


@router.get(
    "/{scan_id}/reports",
    response_model=list[dict[str, Any]],
    summary="List reports for an owned scan",
)
async def list_scan_reports(
    scan_id: str,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> list[dict[str, Any]]:
    db = get_db_session()
    try:
        from app.models.report import Report
        from app.models.scan import Scan

        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found.")
        domain = DomainService(db).get_domain(
            domain_id=scan.domain_id,
            user_id=current_user["user_id"],
            user_role=current_user.get("role", "viewer"),
        )
        if not domain:
            raise HTTPException(status_code=404, detail="Scan not found.")

        reports = (
            db.query(Report)
            .filter(Report.scan_id == scan_id)
            .order_by(Report.created_at.desc())
            .all()
        )
        return [
            {
                "id": report.id,
                "scan_id": report.scan_id,
                "title": report.title,
                "status": report.status,
                "format": report.format,
                "created_at": report.created_at.isoformat(),
            }
            for report in reports
        ]
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
        if (
            not report
            or not report.file_path
            or not os.path.isfile(report.file_path)
            or os.path.getsize(report.file_path) == 0
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
        if await asyncio.to_thread(_read_pdf_header, report.file_path) != b"%PDF-":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Stored report is not a valid PDF.",
                )

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
