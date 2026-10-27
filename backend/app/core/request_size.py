"""VIXOR �?" Request size limit middleware (T-010).

Rejects requests whose Content-Length exceeds the configured maximum,
preventing overly large payloads from reaching the application.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger("request_size")
settings = get_settings()


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces a maximum request body size."""

    def __init__(self, app: ASGIApp, max_bytes: int | None = None) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes or settings.MAX_REQUEST_SIZE_BYTES

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                size = int(content_length)
            except ValueError:
                size = 0
            if size > self.max_bytes:
                logger.warning(
                    "request_size_exceeded",
                    path=request.url.path,
                    size=size,
                    max_bytes=self.max_bytes,
                )
                return Response(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content="Request entity too large",
                    media_type="text/plain",
                )
        return await call_next(request)
