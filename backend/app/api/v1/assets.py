"""VIXOR — Assets API endpoints.

GET /domains/{id}/assets - List assets for a domain (ownership-checked).
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.rbac import RequireViewer
from app.deps import get_db, get_db_session
from app.models.asset import Asset
from app.services.domain_service import DomainService

router = APIRouter(prefix="/domains", tags=["assets"])


def get_domain_service(db: Session = Depends(get_db)) -> DomainService:
    return DomainService(db=db)


@router.get(
    "/{domain_id}/assets",
    response_model=list[dict[str, Any]],
    summary="List assets for a domain (ownership-checked)",
)
async def list_assets(
    domain_id: str,
    domain_svc: DomainService = Depends(get_domain_service),
    current_user: dict[str, Any] = Depends(RequireViewer),
) -> list[dict[str, Any]]:
    domain = domain_svc.get_domain(
        domain_id=domain_id,
        user_id=current_user["user_id"],
        user_role=current_user.get("role", "viewer"),
    )
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found.",
        )

    db = get_db_session()
    try:
        assets = db.query(Asset).filter(Asset.domain_id == domain_id).all()

        return [
            {
                "id": a.id,
                "hostname": a.hostname,
                "ips": a.ips,
                "is_live": a.is_live,
                "scope_status": a.scope_status.value,
                "scope_reason": a.scope_reason,
                "technologies": a.technologies,
                "sensitivity_score": a.sensitivity_score,
                "first_seen": a.first_seen.isoformat() if a.first_seen else None,
                "last_seen": a.last_seen.isoformat() if a.last_seen else None,
            }
            for a in assets
        ]
    finally:
        db.close()
