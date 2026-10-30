"""Pytest configuration and shared fixtures for VIXOR backend tests.

Tests use an in-memory SQLite database by default (override DATABASE_URL
to point at a test PostgreSQL instance for integration tests).
"""

import os
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Every pytest process gets a new ignored SQLite database. This prevents the
# suite from ever mutating an existing test.db or a user-supplied database URL.
os.environ["DATABASE_URL"] = f"sqlite:///./.pytest-vixor-{uuid.uuid4().hex}.db"
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault(
    "JWT_SECRET_KEY", "test_secret_key_do_not_use_in_production_32bytes"
)
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
)
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_INITIAL_PASSWORD", "TestPassword123!")
os.environ.setdefault("ZAP_API_KEY", "test_zap_key")
os.environ.setdefault("ZAP_API_URL", "http://zap:8090")
os.environ.setdefault("SCAN_TOOL_TIMEOUT_SECONDS", "1800")
os.environ.setdefault("MAX_CONCURRENT_SCANS_PER_PROJECT", "2")
os.environ.setdefault("REVERIFY_INTERVAL_DAYS", "7")
os.environ.setdefault("ALLOW_PRIVATE_IP_SCANNING", "false")
os.environ.setdefault("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1")

import app.models.asset
import app.models.audit_log
import app.models.correlation
import app.models.domain
import app.models.finding
import app.models.finding_history
import app.models.finding_score
import app.models.project
import app.models.report
import app.models.scan
import app.models.scan_asset
import app.models.schedule
import app.models.user
from app.config import get_settings
from app.main import create_app
from app.models.base import Base


@pytest.fixture(scope="session")
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    settings = get_settings()
    engine = create_engine(
        settings.DATABASE_URL, connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
