"""Authorized attack-surface discovery dispatch endpoint."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.rbac import require_role
from app.deps import get_db
from app.models.domain import DomainStatus
from app.services.domain_service import DomainService
from app.services.scope_guard import is_in_scope

router = APIRouter(prefix="/domains", tags=["discovery"])


def get_domain_service(db: Session = Depends(get_db)) -> DomainService:
    return DomainService(db)


@router.post(
    "/{domain_id}/discover",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue authorized domain discovery",
)
async def discover_domain(
    domain_id: str,
    domain_svc: DomainService = Depends(get_domain_service),
    current_user: dict[str, Any] = Depends(require_role("analyst")),
) -> dict[str, str]:
    domain = domain_svc.get_domain(
        domain_id=domain_id,
        user_id=current_user["user_id"],
        user_role=current_user.get("role", "viewer"),
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found.")
    if domain.status != DomainStatus.verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Domain ownership must be verified before discovery.",
        )

    in_scope, reason = is_in_scope(domain, domain.root_domain, resolve_dns=False)
    if not in_scope:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=reason or "Domain verification is stale.",
        )

    try:
        from app.workers.tasks_discovery import run_discovery

        run_discovery.delay(str(domain.id))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Discovery task queue is unavailable.",
        ) from exc

    return {"domain_id": str(domain.id), "status": "queued"}
