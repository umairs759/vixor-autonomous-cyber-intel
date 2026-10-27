"""VIXOR FastAPI application entry point.

Creates the FastAPI app, configures structured logging, CORS, security
headers, and registers API routers. Health check is available at /health.
"""

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.core.audit_middleware import AuditMiddleware
from app.core.logging import configure_logging, get_logger
from app.core.request_size import RequestSizeMiddleware

configure_logging()
logger = get_logger("main")
settings = get_settings()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request and log it."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.time()
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception("unhandled_request_error", error=str(exc))
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )
        process_time = (time.time() - start) * 1000
        response.headers["x-request-id"] = request_id
        response.headers["x-process-time-ms"] = f"{process_time:.2f}"
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time_ms=round(process_time, 2),
        )
        structlog.contextvars.clear_contextvars()
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add hardening security headers to every response."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        # HSTS only when served over HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title="VIXOR — Autonomous Vulnerability Intelligence Platform",
        version="0.1.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        RequestIDMiddleware,
    )
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RequestSizeMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        max_age=600,
    )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "vixor-api"}

    # API routers
    from app.api.v1 import assets as assets_api
    from app.api.v1 import auth as auth_api
    from app.api.v1 import correlations as correlations_api
    from app.api.v1 import dashboard as dashboard_api
    from app.api.v1 import domains as domains_api
    from app.api.v1 import findings as findings_api
    from app.api.v1 import projects as projects_api
    from app.api.v1 import reports as reports_api
    from app.api.v1 import scans as scans_api
    from app.api.v1 import schedules as schedules_api
    from app.api.v1 import users as users_api

    app.include_router(auth_api.router, prefix="/api/v1")
    app.include_router(users_api.router, prefix="/api/v1")
    app.include_router(projects_api.router, prefix="/api/v1")
    app.include_router(domains_api.router, prefix="/api/v1")
    app.include_router(assets_api.router, prefix="/api/v1")
    app.include_router(scans_api.router, prefix="/api/v1")
    app.include_router(findings_api.router, prefix="/api/v1")
    app.include_router(correlations_api.router, prefix="/api/v1")
    app.include_router(reports_api.router, prefix="/api/v1")
    app.include_router(schedules_api.router, prefix="/api/v1")
    app.include_router(dashboard_api.router, prefix="/api/v1")

    return app


app = create_app()
