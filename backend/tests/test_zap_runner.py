"""Unit tests for OWASP ZAP runner (T-027).

Tests use mocked httpx since ZAP daemon is not available locally.
Covers:
- Valid target runs active_scan with safe policy params
- Invalid target returns error dict
- Missing scan id returns error
- Non-200 / error response handled
- Poll loop ends on status >= 100
- Alerts returned in result
- Non-destructive: uses httpx client (shell=False), allowlisted API paths
"""

from unittest.mock import MagicMock, patch

from app.services.scanning.zap_runner import ZapRunner


class TestZapRunner:
    """Tests for ZapRunner."""

    def test_valid_target_runs_active_scan(self):
        """Valid target triggers ZAP active_scan with safe params."""
        runner = ZapRunner(zap_url="http://zap:8090", api_key="testkey")

        mock_response = MagicMock()
        mock_response.content = b'{"scan": "123"}'
        mock_response.json = MagicMock(return_value={"scan": "123"})

        status_response = MagicMock()
        status_response.content = b'{"status": "100"}'
        status_response.json = MagicMock(return_value={"status": "100"})

        alerts_response = MagicMock()
        alerts_response.content = b'{"alerts": [{"alert": "XSS"}]}'
        alerts_response.json = MagicMock(return_value={"alerts": [{"alert": "XSS"}]})

        with patch(
            "app.services.scanning.zap_runner.httpx.Client"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = False
            mock_client.request.side_effect = [
                mock_response,
                status_response,
                alerts_response,
            ]

            result = runner.active_scan("https://example.com")

        assert result["target"] == "https://example.com"
        assert result["scan_id"] == "123"
        assert result["alerts"] == [{"alert": "XSS"}]

        # Verify allowlisted API path used
        call_args = mock_client.request.call_args_list
        assert any("scan/" in str(c) for c in call_args)

    def test_invalid_target_returns_error(self):
        """Invalid target hostname returns error dict without calling ZAP."""
        runner = ZapRunner()

        with patch(
            "app.services.scanning.zap_runner.httpx.Client"
        ) as mock_client_class:
            result = runner.active_scan("not a hostname")

        assert "error" in result
        assert result["target"] == "not a hostname"
        mock_client_class.assert_not_called()

    def test_empty_target_returns_error(self):
        """Empty target returns error dict."""
        runner = ZapRunner()

        with patch(
            "app.services.scanning.zap_runner.httpx.Client"
        ) as mock_client_class:
            result = runner.active_scan("")

        assert "error" in result
        mock_client_class.assert_not_called()

    def test_missing_scan_id_returns_error(self):
        """Failed scan start returns error dict."""
        runner = ZapRunner()

        mock_response = MagicMock()
        mock_response.content = b"{}"
        mock_response.json = MagicMock(return_value={})

        with patch(
            "app.services.scanning.zap_runner.httpx.Client"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = False
            mock_client.request.return_value = mock_response

            result = runner.active_scan("https://example.com")

        assert "error" in result
        assert result["error"] == "failed to start scan"

    def test_poll_ends_at_100(self):
        """Status polling stops when progress reaches 100."""
        runner = ZapRunner(timeout_seconds=60)

        scan_response = MagicMock()
        scan_response.content = b'{"scan": "1"}'
        scan_response.json = MagicMock(return_value={"scan": "1"})

        status_50 = MagicMock()
        status_50.content = b'{"status": "50"}'
        status_50.json = MagicMock(return_value={"status": "50"})

        status_100 = MagicMock()
        status_100.content = b'{"status": "100"}'
        status_100.json = MagicMock(return_value={"status": "100"})

        alerts_response = MagicMock()
        alerts_response.content = b'{"alerts": []}'
        alerts_response.json = MagicMock(return_value={"alerts": []})

        with patch(
            "app.services.scanning.zap_runner.httpx.Client"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = False
            mock_client.request.side_effect = [
                scan_response,
                status_50,
                status_100,
                alerts_response,
            ]

            with patch("app.services.scanning.zap_runner.time.sleep"):
                result = runner.active_scan("https://example.com")

        assert result["scan_id"] == "1"
        assert result["alerts"] == []

    def test_no_alerts_returns_empty_list(self):
        """Scan with no alerts returns empty alerts list."""
        runner = ZapRunner()

        scan_response = MagicMock()
        scan_response.content = b'{"scan": "1"}'
        scan_response.json = MagicMock(return_value={"scan": "1"})

        status_response = MagicMock()
        status_response.content = b'{"status": "100"}'
        status_response.json = MagicMock(return_value={"status": "100"})

        alerts_response = MagicMock()
        alerts_response.content = b'{"alerts": []}'
        alerts_response.json = MagicMock(return_value={"alerts": []})

        with patch(
            "app.services.scanning.zap_runner.httpx.Client"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = False
            mock_client.request.side_effect = [
                scan_response,
                status_response,
                alerts_response,
            ]

            with patch("app.services.scanning.zap_runner.time.sleep"):
                result = runner.active_scan("https://example.com")

        assert result["alerts"] == []

    def test_api_key_passed(self):
        """API key is included in request params."""
        runner = ZapRunner(api_key="secretkey")

        scan_response = MagicMock()
        scan_response.content = b'{"scan": "1"}'
        scan_response.json = MagicMock(return_value={"scan": "1"})

        status_response = MagicMock()
        status_response.content = b'{"status": "100"}'
        status_response.json = MagicMock(return_value={"status": "100"})

        alerts_response = MagicMock()
        alerts_response.content = b'{"alerts": []}'
        alerts_response.json = MagicMock(return_value={"alerts": []})

        with patch(
            "app.services.scanning.zap_runner.httpx.Client"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = False
            mock_client.request.side_effect = [
                scan_response,
                status_response,
                alerts_response,
            ]

            with patch("app.services.scanning.zap_runner.time.sleep"):
                runner.active_scan("https://example.com")

        # apikey should be in the params of the scan request
        call_kwargs = mock_client.request.call_args_list[0].kwargs
        assert call_kwargs.get("params", {}).get("apikey") == "secretkey"

    def test_request_exception_handled(self):
        """ZAP API request exception returns error dict without crashing."""
        runner = ZapRunner()

        with patch(
            "app.services.scanning.zap_runner.httpx.Client"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = False
            mock_client.request.side_effect = Exception("connection refused")

            result = runner.active_scan("https://example.com")

        assert "error" in result
