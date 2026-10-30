"""VIXOR — Findings API endpoints.

GET /findings/{id} - Get finding details (ownership-checked).
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.rbac import require_role

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get(
    "/{finding_id}",
    response_model=dict,
    summary="Get finding details (ownership-checked)",
)
async def get_finding(
    finding_id: str,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> dict[str, Any]:
    from app.deps import get_db_session

    db = get_db_session()

    try:
        from app.models.finding import Finding

        finding = db.query(Finding).filter(Finding.id == finding_id).first()
        if not finding:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Finding not found.",
            )

        # Ownership check through scan -> domain
        from app.models.scan import Scan

        scan = db.query(Scan).filter(Scan.id == finding.scan_id).first()
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Finding not found.",
            )

        from app.services.domain_service import DomainService

        domain_svc = DomainService(db)
        domain = domain_svc.get_domain(
            domain_id=scan.domain_id,
            user_id=current_user["user_id"],
            user_role=current_user.get("role", "viewer"),
        )

        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Finding not found.",
            )

        # Get ML risk score
        from app.models.finding_score import FindingScore
        score = db.query(FindingScore).filter(FindingScore.finding_id == finding.id).first()

        # Get regression status from finding history
        from app.models.finding_history import FindingHistory
        history = db.query(FindingHistory).filter(
            FindingHistory.fingerprint == finding.fingerprint,
            FindingHistory.asset_id == finding.asset_id
        ).order_by(FindingHistory.created_at.desc()).first()

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
            "score": {
                "risk_score": score.risk_score if score else None,
                "risk_class": score.risk_class.value if score else None,
                "model_version": score.model_version if score else None,
                "features": score.features if score else {},
                "shap_values": score.shap_values if score else {},
                "narrative": score.narrative if score else None,
                "scored_by": score.scored_by.value if score else None,
            } if score else None,
            "regression_status": history.status.value if history else None,
        }
    finally:
        db.close()
