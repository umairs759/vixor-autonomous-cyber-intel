"""VIXOR — Users admin API endpoints (T-016).

GET/POST /users, PATCH /users/{id} — admin only.
GET /admin/audit-logs — admin only.
All ownership checks, RBAC, and audit-logged.
"""

from typing import Any

import redis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.rbac import require_role
from app.deps import get_db
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.redis import get_redis
from app.schemas.user import (
    AuditLogResponse,
    CreateUserRequest,
    UpdateUserRequest,
    UserResponse,
)
from app.services.audit_service import write_audit_log
from app.services.auth_service import AuthService

router = APIRouter(prefix="/users", tags=["users"])


def get_auth_service(
    db: Session = Depends(get_db),
    redis: redis.Redis = Depends(get_redis),
) -> AuthService:
    return AuthService(db=db, redis_client=redis)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user (admin only)",
)
async def create_user(
    request: Request,
    user_data: CreateUserRequest,
    auth: AuthService = Depends(get_auth_service),
    current_user: dict[str, Any] = Depends(require_role("admin")),
) -> UserResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Check if email already exists
    existing = auth.db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists.",
        )

    # Validate role
    try:
        role = UserRole(user_data.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be one of: admin, analyst, viewer.",
        )

    password_hash = AuthService.hash_password_static(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=password_hash,
        role=role,
        is_active=True,
    )
    auth.db.add(new_user)
    auth.db.commit()
    auth.db.refresh(new_user)

    write_audit_log(
        auth.db,
        action="user_created",
        resource_type="user",
        resource_id=new_user.id,
        user_id=current_user["user_id"],
        ip=client_ip,
        user_agent=user_agent,
        metadata={"email": new_user.email, "role": new_user.role.value},
    )

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        role=new_user.role.value,
        is_active=new_user.is_active,
        created_at=new_user.created_at.isoformat(),
    )


@router.get(
    "",
    response_model=list[UserResponse],
    summary="List all users (admin only)",
)
async def list_users(
    auth: AuthService = Depends(get_auth_service),
    current_user: dict[str, Any] = Depends(require_role("admin")),
) -> list[UserResponse]:
    users = auth.db.query(User).all()
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            role=u.role.value,
            is_active=u.is_active,
            created_at=u.created_at.isoformat(),
        )
        for u in users
    ]


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user (admin only)",
)
async def update_user(
    request: Request,
    user_id: str,
    user_data: UpdateUserRequest,
    auth: AuthService = Depends(get_auth_service),
    current_user: dict[str, Any] = Depends(require_role("admin")),
) -> UserResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    user = auth.db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user_data.email is not None:
        existing = (
            auth.db.query(User)
            .filter(User.email == user_data.email, User.id != user_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists.",
            )
        user.email = user_data.email

    if user_data.password is not None:
        user.password_hash = AuthService.hash_password_static(
            user_data.password
        )

    if user_data.role is not None:
        try:
            user.role = UserRole(user_data.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be one of: admin, analyst, viewer.",
            )

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    auth.db.commit()
    auth.db.refresh(user)

    write_audit_log(
        auth.db,
        action="user_updated",
        resource_type="user",
        resource_id=user.id,
        user_id=current_user["user_id"],
        ip=client_ip,
        user_agent=user_agent,
        metadata={"updated_fields": user_data.model_dump(exclude_unset=True)},
    )

    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.get(
    "/audit-logs",
    response_model=list[AuditLogResponse],
    summary="Get audit logs (admin only)",
)
async def get_audit_logs(
    auth: AuthService = Depends(get_auth_service),
    current_user: dict[str, Any] = Depends(require_role("admin")),
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLogResponse]:
    logs = (
        auth.db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        AuditLogResponse(
            id=l.id,
            user_id=l.user_id,
            action=l.action,
            resource_type=l.resource_type,
            resource_id=l.resource_id,
            ip=l.ip,
            user_agent=l.user_agent,
            metadata=l.event_metadata,
            created_at=l.created_at.isoformat(),
        )
        for l in logs
    ]
