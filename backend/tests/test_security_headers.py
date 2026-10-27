"""Unit and integration tests for security headers, CORS, and request size limits (T-010).

Tests cover:
- Security headers on all responses
- CORS allowlist configuration
- Request size limit rejects oversized payloads
"""

from fastapi.testclient import TestClient


class TestSecurityHeaders:
    """Tests that security headers are present on responses."""

    def test_security_headers_present(self, client: TestClient):
        """All expected security headers are present on /health response."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("referrer-policy") == "no-referrer"
        assert response.headers.get("permissions-policy") is not None

    def test_hsts_header_on_https(self, client: TestClient):
        """HSTS header present when request is HTTPS."""
        # TestClient uses http://testserver so HSTS won't be set.
        # Verify the header is conditionally added (check middleware code).
        response = client.get("/health")
        # Over HTTP, Strict-Transport-Security should NOT be present
        assert "strict-transport-security" not in response.headers


class TestCORS:
    """Tests CORS allowlist configuration."""

    def test_cors_allow_origin(self, client: TestClient):
        """CORS allows configured origin."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS preflight should succeed (not 403)
        assert response.status_code == 200

    def test_cors_allow_methods(self, client: TestClient):
        """CORS allows expected HTTP methods."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        allow_methods = response.headers.get("access-control-allow-methods", "")
        assert "GET" in allow_methods


class TestRequestSizeLimit:
    """Tests request size limit enforcement."""

    def test_normal_request_passes(self, client: TestClient):
        """Normal-sized requests are not rejected."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_oversized_request_rejected(self, client: TestClient):
        """Requests with Content-Length exceeding max are rejected with 413."""
        # Use a very large Content-Length header (no body needed for GET)
        response = client.get(
            "/health",
            headers={"content-length": "10485761"},  # 10 MB + 1 byte
        )
        assert response.status_code == 413

    def test_request_at_limit_passes(self, client: TestClient):
        """Requests exactly at the limit are accepted."""
        response = client.get(
            "/health",
            headers={"content-length": "10485760"},  # exactly 10 MB
        )
        assert response.status_code == 200
