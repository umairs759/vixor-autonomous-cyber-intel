"""Structured JSON logging for VIXOR.

Configures structlog to emit JSON logs with request IDs. Secrets,
tokens, and password hashes are never logged.
"""

import logging
import sys
from typing import Any

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog + standard library logging for JSON output."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)


# Redact sensitive fields from any log event
_SENSITIVE_KEYS = {
    "password", "password_hash", "token", "access_token", "refresh_token",
    "jwt_secret", "secret_key", "api_key", "authorization", "cookie",
}


def redact_event(event_dict: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive values from a log event dict before rendering."""
    for key in list(event_dict.keys()):
        lk = key.lower()
        if any(s in lk for s in _SENSITIVE_KEYS):
            event_dict[key] = "[REDACTED]"
    return event_dict
