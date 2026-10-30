"""VIXOR — Security core (T-015).

Password hashing with argon2id, JWT creation/validation, and secure
token comparison. Never logs secrets or hashes.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.low_level import Type
from jose import jwt  # type: ignore[import-untyped]

from app.config import get_settings

settings = get_settings()

# Argon2id hasher
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def hash_password(password: str) -> str:
    """Hash a password using argon2id."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against an argon2id hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except Exception:  # noqa: BLE001 - argon2 may raise various exceptions on invalid hash
        return False


def create_access_token(
    user_id: str,
    role: str,
    jti: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed access JWT.

    Claims: sub (user_id), role, jti, exp, iat.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "jti": jti,
        "token_type": "access",
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    secret = settings.JWT_SECRET_KEY
    if secret is None:
        raise ValueError("JWT_SECRET_KEY is not configured")
    encoded_jwt: str = jwt.encode(to_encode, secret, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access JWT. Raises on invalid/expired."""
    secret = settings.JWT_SECRET_KEY
    if secret is None:
        raise ValueError("JWT_SECRET_KEY is not configured")
    decoded: Any = jwt.decode(
        token,
        secret,
        algorithms=[settings.JWT_ALGORITHM],
        options={"verify_sub": False},
    )
    return decoded  # type: ignore[no-any-return]


def constant_time_compare(a: str, b: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    import hmac

    return hmac.compare_digest(a, b)
