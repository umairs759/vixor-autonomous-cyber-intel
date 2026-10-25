"""Tests for the /health endpoint (T-002)."""

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "vixor-api"


def test_health_has_request_id_header(client: TestClient):
    response = client.get("/health")
    assert "x-request-id" in response.headers
    assert "x-process-time-ms" in response.headers
