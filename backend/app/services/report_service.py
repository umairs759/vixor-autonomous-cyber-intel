"""VIXOR - PDF report service (T-040).

Generates PDF reports (executive summary, severity chart, findings,
remediation, regression) using ReportLab. No external network.
"""

from __future__ import annotations

import os
from typing import Any

from reportlab.graphics.charts.barcharts import VerticalBarChart  # type: ignore[import-untyped]
from reportlab.graphics.shapes import Drawing  # type: ignore[import-untyped]
from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import letter  # type: ignore[import-untyped]
from reportlab.lib.styles import getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.lib.units import inch  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.logging import get_logger
from app.models.finding import Finding
from app.models.finding_score import FindingScore
from app.models.report import Report
from app.models.scan import Scan

logger = get_logger("reporting")

REPORTS_DIR = os.environ.get("VIXOR_REPORTS_DIR", "reports")


class ReportService:
    """Generate PDF reports for scans."""

    def __init__(self, db_session: Any) -> None:
        self.db = db_session

    def generate_report(self, scan_id: str, output_path: str | None = None) -> Report:
        return self.generate(scan_id, output_path=output_path)

    def generate(self, scan_id: str, output_path: str | None = None) -> Report:
        scan = self.db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise ValueError("scan not found")

        if output_path is None:
            os.makedirs(REPORTS_DIR, exist_ok=True)
            output_path = os.path.join(REPORTS_DIR, f"{scan_id}.pdf")

        findings = self.db.query(Finding).filter(Finding.scan_id == scan_id).all()
        scores = {
            s.finding_id: s
            for s in self.db.query(FindingScore).filter(
                FindingScore.finding_id.in_([f.id for f in findings]) if findings else False
            ).all()
        } if findings else {}

        # Severity counts
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for f in findings:
            sev = (f.severity_raw or "info").lower()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story: list[Any] = []

        story.append(Paragraph(f"VIXOR Scan Report - {scan_id}", styles["Title"]))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"Project: {scan.project_id}", styles["Normal"]))
        story.append(Paragraph(f"Domain: {scan.domain_id}", styles["Normal"]))
        story.append(Paragraph(f"Status: {scan.status}", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        # Executive summary
        story.append(Paragraph("Executive Summary", styles["Heading2"]))
        total = len(findings)
        story.append(Paragraph(f"Total findings: {total}", styles["Normal"]))
        for sev, count in severity_counts.items():
            story.append(Paragraph(f"{sev.title()}: {count}", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        # Severity chart
        drawing = Drawing(400, 200)
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 50
        chart.height = 125
        chart.width = 300
        chart.data = [[severity_counts.get(s, 0) for s in ("critical", "high", "medium", "low", "info")]]
        chart.categoryAxis.categoryNames = ["Critical", "High", "Medium", "Low", "Info"]
        chart.valueAxis.valueMin = 0
        drawing.add(chart)
        story.append(drawing)
        story.append(Spacer(1, 0.2 * inch))

        # Findings table
        story.append(Paragraph("Findings", styles["Heading2"]))
        table_data = [["Title", "Severity", "Risk Score", "Source"]]
        for f in findings[:100]:
            fs = scores.get(f.id)
            risk = f"{fs.risk_score:.1f}" if fs else "N/A"
            table_data.append(
                [
                    (f.title or "")[:60],
                    (f.severity_raw or "").title(),
                    risk,
                    f.source_tool or "",
                ]
            )
        if len(table_data) > 1:
            table = Table(table_data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(table)
        else:
            story.append(Paragraph("No findings.", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        # Remediation
        story.append(Paragraph("Remediation", styles["Heading2"]))
        seen_remediation: set[str] = set()
        for f in findings:
            rem = (f.remediation or "").strip()
            if rem and rem not in seen_remediation:
                seen_remediation.add(rem)
                story.append(Paragraph(f"- {rem}", styles["Normal"]))
        if not seen_remediation:
            story.append(Paragraph("No remediation guidance.", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        # Regression
        story.append(Paragraph("Regression", styles["Heading2"]))
        try:
            from app.models.finding_history import FindingHistory

            history_rows = (
                self.db.query(FindingHistory)
                .filter(FindingHistory.scan_id == scan_id)
                .all()
            )
            if history_rows:
                for h in history_rows[:50]:
                    story.append(
                        Paragraph(f"{h.fingerprint[:12]}...: {h.status.value}", styles["Normal"])
                    )
            else:
                story.append(Paragraph("No regression history for this scan.", styles["Normal"]))
        except Exception:  # noqa: BLE001
            story.append(Paragraph("Regression data unavailable.", styles["Normal"]))

        doc.build(story)

        report = Report(
            scan_id=scan_id,
            generated_by=scan.triggered_by,
            file_path=output_path,
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        logger.info("report generated", scan_id=scan_id, path=output_path)
        return report

    def generate_pdf(self, scan_id: str, output_path: str | None = None) -> str:
        report = self.generate(scan_id, output_path=output_path)
        return report.file_path


def generate_report_pdf(db_session: Any, scan_id: str, output_path: str | None = None) -> str:
    service = ReportService(db_session)
    return service.generate_pdf(scan_id, output_path=output_path)