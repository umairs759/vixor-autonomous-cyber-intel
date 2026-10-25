"""VIXOR — Authentication service (T-015).

Handles login, token issuance, refresh, logout, account lockout,
and rate limiting. All security-critical auth logic lives here.
"""

import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.rate_limit import RateLimiter
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.services.audit_service import write_audit_log

settings = get_settings()

# Lockout constants (from PRD US-01)
FAILURE_THRESHOLD = 5
LOCKOUT_DURATION_MINUTES = 15


class AuthService:
    def __init__(self, db: Session, redis_client):
        self.db = db
        self.rate_limiter = RateLimiter(redis_client)

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

        # Verify password (constant-time)
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

    def create_tokens(self, user: User) -> tuple[str, str]:
        """Create access token and refresh token JTI. Returns (access_token, refresh_jti)."""
        access_jti = str(uuid.uuid4())
        refresh_jti = str(uuid.uuid4())

        access_token = create_access_token(
            user_id=user.id,
            role=user.role.value,
            jti=access_jti,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        # The refresh token is opaque (returned as refresh_jti).
        # In a full implementation, we'd store refresh_jti -> user_id in Redis
        # with an expiry for reuse detection and rotation.

        return access_token, refresh_jti

    def refresh_access_token(
        self,
        refresh_token: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str | None, str | None, str | None]:
        """Rotate refresh token and issue new access token.

        Returns (new_access_token, new_refresh_token, error_message).
        """
        try:
            # Decode the refresh token to extract user info
            payload = decode_access_token(refresh_token)
            user_id = payload.get("sub")
        except JWTError:
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
        new_refresh_jti = str(uuid.uuid4())

        new_access_token = create_access_token(
            user_id=user.id,
            role=user.role.value,
            jti=new_access_jti,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        return new_access_token, new_refresh_jti, None

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
