"""VIXOR — Auth API endpoints (T-015).

POST /auth/login, POST /auth/refresh, POST /auth/logout.
All inputs validated with Pydantic. Generic error messages to prevent
user enumeration. Audit-logged on success and failure.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.rbac import RequireViewer
from app.deps import get_db
from app.redis import get_redis
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    db: Session = Depends(get_db),
    redis=Depends(get_redis),
) -> AuthService:
    return AuthService(db=db, redis_client=redis)


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
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

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

    access_token, _refresh_jti = auth.create_tokens(user)

    return TokenResponse(
        access_token=access_token,
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
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    new_access_token, _new_refresh_jti, error = auth.refresh_access_token(
        refresh_token=refresh_data.refresh_token,
        ip=client_ip,
        user_agent=user_agent,
    )
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    return TokenResponse(
        access_token=new_access_token,
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
    current_user: dict = Depends(RequireViewer),
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    auth.logout(
        user_id=current_user.get("user_id"),
        ip=client_ip,
        user_agent=user_agent,
    )
