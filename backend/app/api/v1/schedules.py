"""VIXOR — Scan Schedules API endpoints.

POST/GET/DELETE /domains/{id}/schedules - Manage scan schedules (ownership-checked).
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.rbac import require_role
from app.deps import get_db, get_db_session
from app.models.schedule import ScanSchedule
from app.services.domain_service import DomainService

router = APIRouter(prefix="/domains", tags=["schedules"])


def get_domain_service(db: Session = Depends(get_db)) -> DomainService:
    return DomainService(db=db)


@router.post(
    "/{domain_id}/schedules",
    status_code=status.HTTP_201_CREATED,
    summary="Create scan schedule (ownership-checked)",
)
async def create_schedule(
    domain_id: str,
    cron: str,
    domain_svc: DomainService = Depends(get_domain_service),
    current_user: dict[str, Any] = Depends(require_role("analyst")),
) -> dict[str, Any]:
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
        schedule = ScanSchedule(
            domain_id=domain_id,
            cron=cron,
            is_active=True,
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)

        return {
            "id": schedule.id,
            "domain_id": domain_id,
            "cron": schedule.cron,
            "is_active": schedule.is_active,
        }
    finally:
        db.close()


@router.get(
    "/{domain_id}/schedules",
    response_model=list[dict[str, Any]],
    summary="List scan schedules (ownership-checked)",
)
async def list_schedules(
    domain_id: str,
    domain_svc: DomainService = Depends(get_domain_service),
    current_user: dict[str, Any] = Depends(require_role("viewer")),
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
        schedules = (
            db.query(ScanSchedule).filter(ScanSchedule.domain_id == domain_id).all()
        )

        return [
            {
                "id": s.id,
                "domain_id": s.domain_id,
                "cron": s.cron,
                "is_active": s.is_active,
                "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
            }
            for s in schedules
        ]
    finally:
        db.close()


@router.delete(
    "/{domain_id}/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete scan schedule (ownership-checked)",
)
async def delete_schedule(
    domain_id: str,
    schedule_id: str,
    domain_svc: DomainService = Depends(get_domain_service),
    current_user: dict[str, Any] = Depends(require_role("analyst")),
) -> None:
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
        schedule = (
            db.query(ScanSchedule)
            .filter(
                ScanSchedule.id == schedule_id,
                ScanSchedule.domain_id == domain_id,
            )
            .first()
        )
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found.",
            )

        db.delete(schedule)
        db.commit()
    finally:
        db.close()
