"""FastAPI dependency injection helpers.

Database session, current user, and other request-scoped dependencies
are defined here to keep routers thin.
"""

from collections.abc import Generator
from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt  # type: ignore[import-untyped]
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger("deps")

# OAuth2 bearer scheme for access tokens (Authorization: Bearer <token>)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.DATABASE_URL, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker[Session](bind=get_engine(), autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session for the request, then close it."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def get_settings_dep() -> Settings:
    return get_settings()


def get_db_session() -> Session:
    """Return a SQLAlchemy Session for direct (non-Depends) use."""
    return get_session_factory()()


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> dict[str, Any]:
    """Validate the access JWT and return the user payload.

    Raises 401 on missing/expired/invalid tokens with a generic message.
    """
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = token or request.cookies.get("access_token")
    if not token:
        raise credentials_exception
    try:
        secret = settings.JWT_SECRET_KEY
        if secret is None:
            raise credentials_exception
        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_sub": False},
        )
        if payload.get("token_type", "access") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return {
            "user_id": user_id,
            "role": payload.get("role"),
            "jti": payload.get("jti"),
        }
    except JWTError:
        logger.warning("invalid_access_token_attempt")
        raise credentials_exception
