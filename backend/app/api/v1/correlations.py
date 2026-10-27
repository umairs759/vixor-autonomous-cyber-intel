"""VIXOR — Correlations API endpoints.

GET /scans/{id}/correlations - Get correlations for a scan (ownership-checked).
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.rbac import require_role
from app.deps import get_db_session
from app.services.domain_service import DomainService

router = APIRouter(prefix="/scans", tags=["correlations"])


@router.get(
    "/{scan_id}/correlations",
    response_model=list[dict[str, Any]],
    summary="Get correlations for a scan (ownership-checked)",
)
async def get_correlations(
    scan_id: str,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> list[dict[str, Any]]:
    db = get_db_session()
    try:
        from app.models.correlation import Correlation
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

        correlations = (
            db.query(Correlation).filter(Correlation.scan_id == scan_id).all()
        )

        return [
            {
                "id": c.id,
                "asset_id": c.asset_id,
                "title": c.title,
                "narrative": c.narrative,
                "combined_score": c.combined_score,
                "finding_ids": c.finding_ids,
                "created_at": c.created_at.isoformat(),
            }
            for c in correlations
        ]
    finally:
        db.close()
