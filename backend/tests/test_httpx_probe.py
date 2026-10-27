"""Unit tests for httpx probe (T-024).

Tests use mocked subprocess since the httpx binary is not available locally.
Covers:
- Valid hostname runs httpx with correct arguments
- Invalid hostname returns error dict
- Missing binary returns error dict
- Timeout returns error dict
- Non-zero exit returns error dict
- JSON output parsed correctly
- JSON parse error handled gracefully
"""

from unittest.mock import MagicMock, patch

from app.services.discovery.httpx_probe import probe_host


class TestProbeHost:
    """Tests for probe_host."""

    @patch("app.services.discovery.httpx_probe.subprocess.run")
    def test_valid_hostname_runs_httpx(self, mock_run):
        """Valid hostname triggers httpx with correct args."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = probe_host("example.com")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "httpx"
        assert "-u" in args
        assert "https://example.com" in args
        assert "-silent" in args
        assert "-json" in args
        assert "-timeout" in args
        assert "-title" in args
        assert "-td" in args
        assert result["live"] is True

    @patch("app.services.discovery.httpx_probe.subprocess.run")
    def test_json_output_parsed(self, mock_run):
        """JSON output from httpx is parsed into result dict."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"status_code": 200, "title": "Example Page", "technologies": ["PHP"], "url": "https://example.com"}'
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = probe_host("example.com")

        assert result["live"] is True
        assert result["status_code"] == 200
        assert result["title"] == "Example Page"
        assert result["technologies"] == ["PHP"]
        assert result["url"] == "https://example.com"

    @patch("app.services.discovery.httpx_probe.subprocess.run")
    def test_json_parse_error(self, mock_run):
        """JSON parse error returns live=True with parse_error."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not json"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = probe_host("example.com")

        assert result["live"] is True
        assert result["error"] == "parse_error"

    @patch("app.services.discovery.httpx_probe.subprocess.run")
    def test_httpx_not_found(self, mock_run):
        """Missing httpx binary returns error dict."""
        mock_run.side_effect = FileNotFoundError("httpx not found")

        result = probe_host("example.com")

        assert result["live"] is False
        assert result["error"] == "httpx not installed"

    @patch("app.services.discovery.httpx_probe.subprocess.run")
    def test_httpx_timeout(self, mock_run):
        """Timeout returns error dict."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("httpx", 10)

        result = probe_host("example.com")

        assert result["live"] is False
        assert result["error"] == "timeout"

    @patch("app.services.discovery.httpx_probe.subprocess.run")
    def test_httpx_failure(self, mock_run):
        """Non-zero exit returns error dict."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "connection refused"
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        result = probe_host("example.com")

        assert result["live"] is False
        assert result["error"] == "connection refused"

    def test_invalid_hostname(self):
        """Invalid hostname returns error dict."""
        result = probe_host("not a hostname")

        assert result["live"] is False
        assert "error" in result

    def test_empty_hostname(self):
        """Empty hostname returns error dict."""
        result = probe_host("")

        assert result["live"] is False
        assert "error" in result
