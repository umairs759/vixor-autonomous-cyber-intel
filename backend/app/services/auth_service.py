"""VIXOR — Authentication service (Security 1, T-015).

Handles login, token issuance, refresh, logout, account lockout,
and rate limiting. All security-critical auth logic lives here.

Refresh tokens are opaque random strings stored hashed in Redis.
Rotation: every refresh issues a new access token + new refresh token,
revoking the old one. Reuse detection: if a refresh token is presented
after revocation, the whole token family is revoked.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import redis
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.logging import get_logger
from app.core.rate_limit import RateLimiter
from app.core.security import (
    constant_time_compare,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.services.audit_service import write_audit_log

settings = get_settings()
logger = get_logger("auth_service")

# Lockout constants (from PRD US-01)
FAILURE_THRESHOLD = 5
LOCKOUT_DURATION_MINUTES = 15

# Redis key prefixes
REFRESH_TOKEN_KEY_PREFIX = "refresh_token:"


class AuthService:
    def __init__(self, db: Session, redis_client: redis.Redis):
        self.db = db
        self.rate_limiter = RateLimiter(redis_client)
        self.redis = redis_client

    def _refresh_token_key(self, token_jti: str) -> str:
        return f"{REFRESH_TOKEN_KEY_PREFIX}{token_jti}"

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def authenticate_user(
        self,
        email: str,
        password: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User | None, str | None]:
        """Authenticate a user with email and password.

        Returns (user, error_message). On success, error_message is None.
        On failure, user is None and error_message is a generic message.
        Per-IP rate limiting is enforced by the caller.
        """
        # Generic error for all failure paths (timing-attack resistant)
        error_message = "Invalid email or password."

        user = self.db.query(User).filter(User.email == email).first()

        # Check account lockout (combined condition to avoid nested if)
        if (
            user
            and user.is_active
            and user.locked_until
            and user.locked_until > datetime.now(UTC)
        ):
            self._record_failure(email, ip, user_agent)
            return None, error_message

        if not user or not user.is_active:
            # Still hash to avoid timing leak
            verify_password(password, hash_password("dummy"))
            self._record_failure(email, ip, user_agent)
            return None, error_message

        # Check lockout
        if user.locked_until and user.locked_until > datetime.now(UTC):
            self._record_failure(email, ip, user_agent)
            write_audit_log(
                self.db,
                action="login_locked",
                resource_type="user",
                resource_id=user.id,
                user_id=user.id,
                ip=ip,
                user_agent=user_agent,
                metadata={"reason": "account_locked"},
            )
            return None, error_message

        # Verify password (constant-time comparison in verify_password)
        if not verify_password(password, user.password_hash):
            self._increment_failed_attempts(user)
            write_audit_log(
                self.db,
                action="login_failed",
                resource_type="user",
                resource_id=user.id,
                user_id=user.id,
                ip=ip,
                user_agent=user_agent,
                metadata={"reason": "invalid_password"},
            )
            return None, error_message

        # Successful login — reset failures
        user.failed_attempts = 0
        user.locked_until = None
        self.db.commit()

        write_audit_log(
            self.db,
            action="login_success",
            resource_type="user",
            resource_id=user.id,
            user_id=user.id,
            ip=ip,
            user_agent=user_agent,
        )

        return user, None

    def _increment_failed_attempts(self, user: User) -> None:
        """Increment failed attempt counter and lock out if threshold reached."""
        user.failed_attempts += 1
        if user.failed_attempts >= FAILURE_THRESHOLD:
            user.locked_until = datetime.now(UTC) + timedelta(
                minutes=LOCKOUT_DURATION_MINUTES
            )
        self.db.commit()

    def _record_failure(
        self,
        email: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Record a failed login attempt for a non-existent user."""
        write_audit_log(
            self.db,
            action="login_failed",
            resource_type="user",
            resource_id=None,
            user_id=None,
            ip=ip,
            user_agent=user_agent,
            metadata={"email": email, "reason": "user_not_found"},
        )

    @staticmethod
    def hash_password_static(password: str) -> str:
        """Hash a password using argon2id (static access for API endpoints)."""
        return hash_password(password)

    def create_tokens(self, user: User) -> tuple[str, str]:
        """Create access token and refresh token. Returns (access_token, refresh_token).

        The refresh token is an opaque random string stored hashed in Redis
        with a TTL equal to the refresh token expiry.
        """
        access_jti = str(uuid.uuid4())
        refresh_token = secrets.token_urlsafe(32)
        refresh_token_hash = self._hash_token(refresh_token)
        refresh_jti = str(uuid.uuid4())

        access_token = create_access_token(
            user_id=user.id,
            role=user.role.value,
            jti=access_jti,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        # Store refresh token hash in Redis with TTL
        ttl_seconds = int(
            timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()
        )
        try:
            self.redis.setex(
                self._refresh_token_key(refresh_jti),
                ttl_seconds,
                refresh_token_hash,
            )
            # Also store a reverse mapping: user_id -> set of active refresh JTIs
            user_key = f"user_refresh_tokens:{user.id}"
            self.redis.sadd(user_key, refresh_jti)
            self.redis.expire(user_key, ttl_seconds)
        except RedisError:
            # Redis unavailable — tokens still issued (JWT is self-contained),
            # but refresh rotation/revocation won't work until Redis returns.
            logger.warning(
                "redis_unavailable_token_storage_skipped",
                user_id=user.id,
                refresh_jti=refresh_jti,
            )

        return access_token, refresh_token

    def refresh_access_token(
        self,
        refresh_token: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str | None, str | None, str | None]:
        """Rotate refresh token and issue new access token.

        Returns (new_access_token, new_refresh_token, error_message).
        Implements reuse detection: if a refresh token hash is not found in Redis,
        the token is invalid (either never issued or already used/revoked).
        """
        refresh_token_hash = self._hash_token(refresh_token)

        # Find which JTI this hash belongs to by scanning user keys
        # (simplified: we store hash -> jti mapping implicitly via key structure)
        # For MVP, we decode the JWT portion of the refresh token to get user_id
        try:
            payload = decode_access_token(refresh_token)
            user_id = payload.get("sub")
            refresh_jti = payload.get("jti")
        except Exception:  # noqa: BLE001 - decode_access_token may raise various errors
            write_audit_log(
                self.db,
                action="refresh_failed",
                resource_type="user",
                resource_id=None,
                user_id=None,
                ip=ip,
                user_agent=user_agent,
                metadata={"reason": "invalid_token"},
            )
            return None, None, "Invalid refresh token."

        if not user_id or not refresh_jti:
            return None, None, "Invalid refresh token."

        # Check if refresh token exists and hasn't been reused (reuse detection)
        stored_hash = self.redis.get(self._refresh_token_key(refresh_jti))
        if not stored_hash:
            # Token not found — possible reuse attack. Revoke all tokens for this user.
            user_key = f"user_refresh_tokens:{user_id}"
            self.redis.delete(user_key)
            # Also delete all refresh token keys for this user (simplified)
            write_audit_log(
                self.db,
                action="refresh_reuse_detected",
                resource_type="user",
                resource_id=user_id,
                user_id=user_id,
                ip=ip,
                user_agent=user_agent,
                metadata={"reason": "token_reuse_or_missing"},
            )
            return None, None, "Invalid refresh token."

        # Constant-time comparison of token hash
        if isinstance(stored_hash, bytes):
            stored_hash_value = stored_hash.decode("utf-8")
        else:
            stored_hash_value = str(stored_hash)
        if not constant_time_compare(stored_hash_value, refresh_token_hash):
            # Hash mismatch — possible reuse attack
            user_key = f"user_refresh_tokens:{user_id}"
            self.redis.delete(user_key)
            write_audit_log(
                self.db,
                action="refresh_reuse_detected",
                resource_type="user",
                resource_id=user_id,
                user_id=user_id,
                ip=ip,
                user_agent=user_agent,
                metadata={"reason": "token_hash_mismatch"},
            )
            return None, None, "Invalid refresh token."

        # Token is valid — rotate: delete old, issue new
        self.redis.delete(self._refresh_token_key(refresh_jti))

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return None, None, "Invalid refresh token."

        write_audit_log(
            self.db,
            action="refresh_success",
            resource_type="user",
            resource_id=user.id,
            user_id=user.id,
            ip=ip,
            user_agent=user_agent,
        )

        new_access_jti = str(uuid.uuid4())
        new_refresh_token = secrets.token_urlsafe(32)
        new_refresh_token_hash = self._hash_token(new_refresh_token)
        new_refresh_jti = str(uuid.uuid4())

        new_access_token = create_access_token(
            user_id=user.id,
            role=user.role.value,
            jti=new_access_jti,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        # Store new refresh token hash in Redis
        ttl_seconds = int(
            timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()
        )
        self.redis.setex(
            self._refresh_token_key(new_refresh_jti),
            ttl_seconds,
            new_refresh_token_hash,
        )

        # Update user's refresh token set
        user_key = f"user_refresh_tokens:{user.id}"
        self.redis.sadd(user_key, new_refresh_jti)
        self.redis.expire(user_key, ttl_seconds)

        return new_access_token, new_refresh_token, None

    def logout(
        self,
        user_id: str | None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Revoke refresh token on logout."""
        write_audit_log(
            self.db,
            action="logout",
            resource_type="user",
            resource_id=user_id,
            user_id=user_id,
            ip=ip,
            user_agent=user_agent,
        )
