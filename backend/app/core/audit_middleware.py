"""VIXOR �?" Audit logging middleware (T-008).

Automatically writes audit log entries for state-changing HTTP requests
(POST, PUT, PATCH, DELETE) that include a valid Bearer token.
Captures user identity from the JWT and request metadata.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger
from app.deps import get_db_session
from app.services.audit_service import write_audit_log

logger = get_logger("audit_middleware")

# State-changing methods that should be audited
AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _extract_bearer_token(request: Request) -> str | None:
    """Extract the Bearer token from the Authorization header."""
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:]
    return None


def _get_user_id_from_token(token: str) -> str | None:
    """Decode a JWT token to extract the user ID. Returns None on failure."""
    try:
        from jose import JWTError, jwt  # type: ignore[import-untyped]

        from app.config import get_settings

        settings = get_settings()
        secret = settings.JWT_SECRET_KEY
        if secret is None:
            return None
        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_sub": False},
        )
        sub: str | None = payload.get("sub")
        return sub
    except (JWTError, Exception):  # noqa: BLE001 - any token error means no user
        return None


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware that writes audit log entries for state-changing requests."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Only audit state-changing methods
        if request.method not in AUDITED_METHODS:
            return await call_next(request)

        # Capture request info before processing
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        path = request.url.path

        # Try to extract user ID from token
        user_id = None
        token = _extract_bearer_token(request)
        if token:
            user_id = _get_user_id_from_token(token)

        # Process the request
        response = await call_next(request)

        # Write audit log after response is generated
        try:
            db = get_db_session()
            try:
                write_audit_log(
                    db,
                    action=f"{request.method.lower()}_{path.strip('/').replace('/', '_') or 'root'}",
                    resource_type="api_request",
                    resource_id=None,
                    user_id=user_id,
                    ip=client_ip,
                    user_agent=user_agent,
                    metadata={
                        "method": request.method,
                        "path": path,
                        "status_code": response.status_code,
                    },
                )
            finally:
                db.close()
        except Exception:  # audit logging must never break the request
            logger.exception("audit_middleware_write_failed", path=path)

        return response
