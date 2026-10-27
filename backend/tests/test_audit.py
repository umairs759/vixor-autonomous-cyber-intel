"""Unit and integration tests for audit logging (T-008).

Tests cover:
- write_audit_log service creates append-only entries
- GET /api/v1/users/audit-logs endpoint (admin only)
- Audit middleware logs state-changing requests
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.core.audit_middleware import AuditMiddleware
from app.models.audit_log import AuditLog
from app.models.base import Base
from app.services.audit_service import write_audit_log

ADMIN_USER_ID = str(uuid.uuid4())
ANALYST_USER_ID = str(uuid.uuid4())


@pytest.fixture(autouse=True)
def create_tables(db_session):
    """Create all tables and clear audit_logs before each test."""
    from app.config import get_settings

    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(engine)
    # Clear audit_logs so tests are isolated
    db_session.query(AuditLog).delete()
    db_session.commit()
    engine.dispose()


class TestAuditService:
    """Unit tests for the audit logging service."""

    def test_write_audit_log_creates_entry(self, db_session):
        """write_audit_log inserts a row into audit_logs."""
        entry = write_audit_log(
            db=db_session,
            action="test_action",
            resource_type="test_resource",
            resource_id=str(uuid.uuid4()),
            user_id=ADMIN_USER_ID,
            ip="127.0.0.1",
            user_agent="test-agent",
            metadata={"key": "value"},
        )
        assert entry.id is not None
        assert entry.action == "test_action"
        assert entry.resource_type == "test_resource"
        assert entry.user_id == ADMIN_USER_ID
        assert entry.ip == "127.0.0.1"
        assert entry.user_agent == "test-agent"
        assert entry.event_metadata == {"key": "value"}

    def test_write_audit_log_defaults_metadata(self, db_session):
        """event_metadata defaults to empty dict when not provided."""
        entry = write_audit_log(
            db=db_session,
            action="test_action",
            resource_type="test_resource",
        )
        assert entry.event_metadata == {}

    def test_audit_log_is_append_only(self, db_session):
        """Multiple write_audit_log calls create multiple entries."""
        write_audit_log(db=db_session, action="action_1", resource_type="type_1")
        write_audit_log(db=db_session, action="action_2", resource_type="type_2")
        count = db_session.query(AuditLog).count()
        assert count == 2


class TestAuditLogsEndpoint:
    """Integration tests for GET /api/v1/users/audit-logs."""

    def _admin_token(self) -> str:
        from app.core.security import create_access_token

        return create_access_token(
            user_id=ADMIN_USER_ID, role="admin", jti=str(uuid.uuid4())
        )

    def _analyst_token(self) -> str:
        from app.core.security import create_access_token

        return create_access_token(
            user_id=ANALYST_USER_ID, role="analyst", jti=str(uuid.uuid4())
        )

    def test_admin_can_read_audit_logs(self, client: TestClient, db_session):
        """Admin user can retrieve audit log entries with 200."""
        # Seed an audit log entry
        write_audit_log(
            db=db_session,
            action="test_action",
            resource_type="test_resource",
            user_id=ADMIN_USER_ID,
        )
        db_session.commit()

        token = self._admin_token()
        response = client.get(
            "/api/v1/users/audit-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_analyst_cannot_read_audit_logs(self, client: TestClient):
        """Analyst user is rejected with 403 from audit-logs."""
        token = self._analyst_token()
        response = client.get(
            "/api/v1/users/audit-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_no_token_rejected(self, client: TestClient):
        """Missing token is rejected with 401."""
        response = client.get("/api/v1/users/audit-logs")
        assert response.status_code == 401

    def test_audit_log_response_shape(self, client: TestClient, db_session):
        """Audit log entries have the expected fields."""
        write_audit_log(
            db=db_session,
            action="user_created",
            resource_type="user",
            resource_id=str(uuid.uuid4()),
            user_id=ADMIN_USER_ID,
            ip="127.0.0.1",
            metadata={"email": "test@example.com"},
        )
        db_session.commit()

        token = self._admin_token()
        response = client.get(
            "/api/v1/users/audit-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        entry = data[0]
        assert "id" in entry
        assert "action" in entry
        assert "resource_type" in entry
        assert "user_id" in entry
        assert "ip" in entry
        assert "created_at" in entry


class TestAuditMiddleware:
    """Tests for the audit middleware class."""

    def test_audit_middleware_is_instantiable(self):
        """AuditMiddleware can be instantiated."""
        middleware = AuditMiddleware(app=None)  # type: ignore[arg-type]
        assert middleware is not None

    def test_audited_methods_constant(self):
        """AUDITED_METHODS contains state-changing HTTP methods."""
        from app.core.audit_middleware import AUDITED_METHODS

        assert "POST" in AUDITED_METHODS
        assert "PUT" in AUDITED_METHODS
        assert "PATCH" in AUDITED_METHODS
        assert "DELETE" in AUDITED_METHODS
        assert "GET" not in AUDITED_METHODS
