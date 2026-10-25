"""FastAPI dependency injection helpers.

Database session, current user, and other request-scoped dependencies
are defined here to keep routers thin.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings, Settings
from app.core.logging import get_logger

logger = get_logger("deps")

# OAuth2 bearer scheme for access tokens (Authorization: Bearer <token>)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@lru_cache
def get_engine():
    settings = get_settings()
    return create_engine(settings.DATABASE_URL, pool_pre_ping=True)


@lru_cache
def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


def get_db() -> Session:
    """Yield a SQLAlchemy session for the request, then close it."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    """Validate the access JWT and return the user payload.

    Raises 401 on missing/expired/invalid tokens with a generic message.
    """
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_sub": False},
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return {"user_id": user_id, "role": payload.get("role"), "jti": payload.get("jti")}
    except JWTError:
        logger.warning("invalid_access_token_attempt")
        raise credentials_exception
