"""Pytest configuration and shared fixtures for VIXOR backend tests.

Tests use an in-memory SQLite database by default (override DATABASE_URL
to point at a test PostgreSQL instance for integration tests).
"""

import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_do_not_use_in_production_32bytes")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_INITIAL_PASSWORD", "TestPassword123!")
os.environ.setdefault("ZAP_API_KEY", "test_zap_key")
os.environ.setdefault("ZAP_API_URL", "http://zap:8090")
os.environ.setdefault("SCAN_TOOL_TIMEOUT_SECONDS", "1800")
os.environ.setdefault("MAX_CONCURRENT_SCANS_PER_PROJECT", "2")
os.environ.setdefault("REVERIFY_INTERVAL_DAYS", "7")
os.environ.setdefault("ALLOW_PRIVATE_IP_SCANNING", "false")
os.environ.setdefault("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1")

from app.main import create_app  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.deps import get_db  # noqa: E402


@pytest.fixture(scope="session")
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
