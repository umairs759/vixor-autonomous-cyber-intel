"""VIXOR — Auth API endpoints (Security 1, T-015).

POST /auth/login, POST /auth/refresh, POST /auth/logout.
All inputs validated with Pydantic. Generic error messages to prevent
user enumeration. Audit-logged on success and failure.
Per-IP rate limiting enforced on login.
"""

from typing import Any

import redis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.rate_limit import RateLimiter
from app.core.rbac import RequireViewer
from app.deps import get_db
from app.redis import get_redis
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    db: Session = Depends(get_db),
    redis: redis.Redis = Depends(get_redis),
) -> AuthService:
    return AuthService(db=db, redis_client=redis)


def get_rate_limiter(redis: redis.Redis = Depends(get_redis)) -> RateLimiter:
    return RateLimiter(redis_client=redis)


# Login rate limit: 5 requests per minute per IP
LOGIN_RATE_LIMIT = 5
LOGIN_RATE_WINDOW = 60  # seconds


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and issue access + refresh tokens",
)
async def login(
    request: Request,
    login_data: LoginRequest,
    auth: AuthService = Depends(get_auth_service),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")

    # Per-IP rate limiting on login
    allowed, _remaining = rate_limiter.is_allowed(
        key=f"login:{client_ip}",
        limit=LOGIN_RATE_LIMIT,
        window_seconds=LOGIN_RATE_WINDOW,
    )
    if not allowed:
        write_audit_log_from_request(
            auth,
            action="login_rate_limited",
            resource_type="ip",
            resource_id=None,
            user_id=None,
            ip=client_ip,
            user_agent=user_agent,
            metadata={"reason": "rate_limit_exceeded"},
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    user, error = auth.authenticate_user(
        email=login_data.email,
        password=login_data.password,
        ip=client_ip,
        user_agent=user_agent,
    )
    if error or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    access_token, refresh_token = auth.create_tokens(user)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=60 * 15,  # 15 minutes
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token and issue a new access token",
)
async def refresh(
    request: Request,
    refresh_data: RefreshRequest,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    new_access_token, new_refresh_token, error = auth.refresh_access_token(
        refresh_token=refresh_data.refresh_token,
        ip=client_ip,
        user_agent=user_agent,
    )
    if error or new_access_token is None or new_refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=60 * 15,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the refresh token and log out",
)
async def logout(
    request: Request,
    logout_data: LogoutRequest,
    auth: AuthService = Depends(get_auth_service),
    current_user: dict[str, Any] = Depends(RequireViewer),
) -> None:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    auth.logout(
        user_id=current_user["user_id"],
        ip=client_ip,
        user_agent=user_agent,
    )


def write_audit_log_from_request(
    auth: AuthService,
    action: str,
    resource_type: str,
    resource_id: str | None,
    user_id: str | None,
    ip: str | None,
    user_agent: str | None,
    metadata: dict[str, Any],
) -> None:
    from app.services.audit_service import write_audit_log

    write_audit_log(
        auth.db,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        ip=ip,
        user_agent=user_agent,
        metadata=metadata,
    )
