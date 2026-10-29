"""Unit tests for WebSocket progress endpoint (T-031).

Tests mock Redis pub/sub and the database session since live Redis and
external targets are not available in test environments. Covers:
- Missing token rejected (1008)
- Invalid JWT token rejected (1008)
- Scan not found rejected (1008)
- User without domain access rejected (1008)
- Valid connection receives Redis pub/sub progress messages
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_access_token
from app.main import create_app


class TestWebSocketAuth:
    """Tests for WebSocket authentication and authorization."""

    @pytest.fixture
    def client(self):
        return TestClient(create_app())

    def _token(self, role="viewer"):
        return create_access_token(user_id="user-1", role=role, jti="jti-1")

    def _db_with_scan(self, scan_exists=True, domain_access=True):
        """Return a mocked db session and DomainService."""
        db = MagicMock()
        scan = MagicMock()
        scan.id = "scan-1"
        scan.domain_id = "domain-1"
        if scan_exists:
            db.query.return_value.filter.return_value.first.return_value = scan
        else:
            db.query.return_value.filter.return_value.first.return_value = None

        domain_svc = MagicMock()
        if domain_access:
            domain_svc.get_domain.return_value = MagicMock()
        else:
            domain_svc.get_domain.return_value = None

        return db, domain_svc

    def test_missing_token_rejected(self, client):
        """WebSocket without token is rejected with 1008."""
        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect("/api/v1/scans/scan-1/ws") as ws,
        ):
            ws.receive_text()

    def test_invalid_token_rejected(self, client):
        """WebSocket with invalid token is rejected with 1008."""
        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect(
                "/api/v1/scans/scan-1/ws?token=invalid.token.value"
            ) as ws,
        ):
            ws.receive_text()

    def test_scan_not_found_rejected(self, client):
        """WebSocket for nonexistent scan is rejected."""
        token = self._token()
        db, _ = self._db_with_scan(scan_exists=False, domain_access=False)
        with (
            patch("app.api.v1.ws.get_db_session", return_value=db),
            patch("app.api.v1.ws.get_redis_client"),
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect(f"/api/v1/scans/scan-1/ws?token={token}") as ws,
        ):
            ws.receive_text()

    def test_no_access_rejected(self, client):
        """WebSocket for scan the user cannot access is rejected."""
        token = self._token()
        db, domain_svc = self._db_with_scan(scan_exists=True, domain_access=False)
        with (
            patch("app.api.v1.ws.get_db_session", return_value=db),
            patch("app.api.v1.ws.get_redis_client"),
            patch("app.api.v1.ws.DomainService", return_value=domain_svc),
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect(f"/api/v1/scans/scan-1/ws?token={token}") as ws,
        ):
            ws.receive_text()

    def test_valid_connection_receives_messages(self, client):
        """Valid authenticated connection receives pub/sub messages."""
        token = self._token()

        messages = [
            '{"scan_id": "scan-1", "status": "running", "progress": 10}',
            '{"scan_id": "scan-1", "status": "completed", "findings": 3}',
        ]

        def fake_pubsub_loop(channel, queue, loop):
            for m in messages:
                queue.put_nowait(m)
            queue.put_nowait(None)  # signal end

        db, domain_svc = self._db_with_scan(scan_exists=True, domain_access=True)
        with (
            patch("app.api.v1.ws.get_db_session", return_value=db),
            patch("app.api.v1.ws.get_redis_client"),
            patch("app.api.v1.ws.DomainService", return_value=domain_svc),
            patch("app.api.v1.ws._redis_pubsub_loop", side_effect=fake_pubsub_loop),
            client.websocket_connect(f"/api/v1/scans/scan-1/ws?token={token}") as ws,
        ):
            data1 = ws.receive_text()
            data2 = ws.receive_text()
            assert "running" in data1
            assert "completed" in data2
