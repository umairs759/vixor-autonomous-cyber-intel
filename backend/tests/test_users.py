"""Unit and integration tests for users admin endpoints (T-016).

Tests cover:
- POST /api/v1/users - create user (admin only)
- GET /api/v1/users - list users (admin only)
- PATCH /api/v1/users/{id} - update user (admin only)
- GET /api/v1/users/audit-logs - audit logs (admin only)
- RBAC: non-admin users rejected with 403
- Unauthenticated requests rejected with 401
- Validation: duplicate email (409), invalid role (400)
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.user import User


@pytest.fixture(autouse=True)
def create_tables(db_session):
    """Create all tables and clear users/audit_logs before each test."""
    from app.config import get_settings

    settings = get_settings()
    from sqlalchemy import create_engine

    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(engine)
    db_session.query(User).delete()
    db_session.query(AuditLog).delete()
    db_session.commit()
    engine.dispose()


def _make_email(prefix: str = "user") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}@example.com"


class TestUsersAdmin:
    """Integration tests for users admin API endpoints."""

    def _admin_token(self) -> str:
        from app.core.security import create_access_token

        return create_access_token(
            user_id=str(uuid.uuid4()), role="admin", jti=str(uuid.uuid4())
        )

    def _analyst_token(self) -> str:
        from app.core.security import create_access_token

        return create_access_token(
            user_id=str(uuid.uuid4()), role="analyst", jti=str(uuid.uuid4())
        )

    def test_create_user_admin(self, client: TestClient, db_session):
        """Admin can create a new user with 201."""
        token = self._admin_token()
        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": _make_email("newuser"),
                "password": "SecurePassword123!",
                "role": "analyst",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"].endswith("@example.com")
        assert data["role"] == "analyst"
        assert data["is_active"] is True
        assert "id" in data

    def test_create_user_analyst_rejected(self, client: TestClient):
        """Analyst cannot create users (403)."""
        token = self._analyst_token()
        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": _make_email("newuser"),
                "password": "SecurePassword123!",
                "role": "viewer",
            },
        )
        assert response.status_code == 403

    def test_create_user_no_token_rejected(self, client: TestClient):
        """Missing token is rejected with 401."""
        response = client.post(
            "/api/v1/users",
            json={
                "email": _make_email("newuser"),
                "password": "SecurePassword123!",
                "role": "analyst",
            },
        )
        assert response.status_code == 401

    def test_create_user_duplicate_email(self, client: TestClient, db_session):
        """Creating a user with existing email returns 409."""
        from app.models.user import UserRole
        from app.services.auth_service import AuthService

        # Seed an existing user
        email = _make_email("existing")
        db_session.add(
            User(
                email=email,
                password_hash=AuthService.hash_password_static("Password123!"),
                role=UserRole.viewer,
                is_active=True,
            )
        )
        db_session.commit()

        token = self._admin_token()
        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": email,
                "password": "SecurePassword123!",
                "role": "analyst",
            },
        )
        assert response.status_code == 409

    def test_create_user_invalid_role(self, client: TestClient):
        """Invalid role returns 400."""
        token = self._admin_token()
        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": _make_email("invalidrole"),
                "password": "SecurePassword123!",
                "role": "superuser",
            },
        )
        assert response.status_code == 400

    def test_list_users_admin(self, client: TestClient, db_session):
        """Admin can list users with 200."""
        token = self._admin_token()
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_users_analyst_rejected(self, client: TestClient):
        """Analyst cannot list users (403)."""
        token = self._analyst_token()
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_update_user_admin(self, client: TestClient, db_session):
        """Admin can update a user with 200."""
        from app.models.user import UserRole
        from app.services.auth_service import AuthService

        # Seed a user to update
        email = _make_email("update")
        user = User(
            email=email,
            password_hash=AuthService.hash_password_static("Password123!"),
            role=UserRole.viewer,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token = self._admin_token()
        response = client.patch(
            f"/api/v1/users/{user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "analyst", "is_active": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "analyst"
        assert data["is_active"] is False

    def test_update_user_nonexistent(self, client: TestClient):
        """Updating a nonexistent user returns 404."""
        token = self._admin_token()
        response = client.patch(
            f"/api/v1/users/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "analyst"},
        )
        assert response.status_code == 404

    def test_get_audit_logs_admin(self, client: TestClient):
        """Admin can read audit logs with 200."""
        token = self._admin_token()
        response = client.get(
            "/api/v1/users/audit-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_audit_logs_analyst_rejected(self, client: TestClient):
        """Analyst cannot read audit logs (403)."""
        token = self._analyst_token()
        response = client.get(
            "/api/v1/users/audit-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
