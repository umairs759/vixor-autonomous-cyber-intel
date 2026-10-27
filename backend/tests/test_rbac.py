"""Unit and integration tests for RBAC dependency (T-007).

Tests cover:
- require_role dependency: admin > analyst > viewer hierarchy
- RequireAdmin, RequireAnalyst, RequireViewer dependencies
- Integration: role-based access to API endpoints via TestClient
- Unauthenticated requests rejected with 401
"""

import uuid

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.rbac import RequireAdmin, RequireAnalyst, RequireViewer, require_role
from app.core.security import create_access_token


class TestRequireRoleUnit:
    """Unit tests for the require_role dependency factory."""

    def test_admin_passes_admin(self):
        dep = require_role("admin")
        user = dep(current_user={"user_id": "u1", "role": "admin"})
        assert user["role"] == "admin"

    def test_analyst_fails_admin(self):
        dep = require_role("admin")
        try:
            dep(current_user={"user_id": "u2", "role": "analyst"})
            assert False, "Expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 403

    def test_viewer_fails_admin(self):
        dep = require_role("admin")
        try:
            dep(current_user={"user_id": "u3", "role": "viewer"})
            assert False, "Expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 403

    def test_viewer_passes_viewer(self):
        dep = require_role("viewer")
        user = dep(current_user={"user_id": "u4", "role": "viewer"})
        assert user["role"] == "viewer"

    def test_analyst_passes_viewer(self):
        # Analyst has higher role than viewer
        dep = require_role("viewer")
        user = dep(current_user={"user_id": "u5", "role": "analyst"})
        assert user["role"] == "analyst"

    def test_admin_passes_viewer(self):
        dep = require_role("viewer")
        user = dep(current_user={"user_id": "u6", "role": "admin"})
        assert user["role"] == "admin"

    def test_analyst_passes_analyst(self):
        dep = require_role("analyst")
        user = dep(current_user={"user_id": "u7", "role": "analyst"})
        assert user["role"] == "analyst"

    def test_viewer_fails_analyst(self):
        dep = require_role("analyst")
        try:
            dep(current_user={"user_id": "u8", "role": "viewer"})
            assert False, "Expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 403

    def test_unknown_role_defaults_viewer(self):
        dep = require_role("viewer")
        user = dep(current_user={"user_id": "u9", "role": "unknown"})
        assert user["role"] == "unknown"

    def test_unknown_role_fails_analyst(self):
        dep = require_role("analyst")
        try:
            dep(current_user={"user_id": "u10", "role": "unknown"})
            assert False, "Expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 403


class TestRequireRoleDependencies:
    """Tests for the pre-built Require* dependencies."""

    def test_require_admin_is_dependency(self):
        assert RequireAdmin is not None

    def test_require_analyst_is_dependency(self):
        assert RequireAnalyst is not None

    def test_require_viewer_is_dependency(self):
        assert RequireViewer is not None


class TestRBACIntegration:
    """Integration tests for RBAC via FastAPI TestClient."""

    def test_admin_passes_rbac_check(self, client: TestClient):
        """Admin user passes RBAC check on admin-protected route (no 403)."""
        token = create_access_token(
            user_id="admin-user", role="admin", jti=str(uuid.uuid4())
        )
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        # RBAC passes for admin (not 403); 500 would be a DB issue, not RBAC
        assert response.status_code != 403

    def test_analyst_cannot_access_admin_route(self, client: TestClient):
        """Analyst user is rejected from admin-protected routes with 403."""
        token = create_access_token(
            user_id="analyst-user", role="analyst", jti=str(uuid.uuid4())
        )
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_viewer_cannot_access_admin_route(self, client: TestClient):
        """Viewer user is rejected from admin-protected routes with 403."""
        token = create_access_token(
            user_id="viewer-user", role="viewer", jti=str(uuid.uuid4())
        )
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_no_token_rejected(self, client: TestClient):
        """Requests without a token are rejected with 401."""
        response = client.get("/api/v1/users")
        assert response.status_code == 401

    def test_invalid_token_rejected(self, client: TestClient):
        """Requests with an invalid token are rejected with 401."""
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_viewer_can_access_health(self, client: TestClient):
        """Viewer (or unauthenticated) can access /health."""
        response = client.get("/health")
        assert response.status_code == 200
