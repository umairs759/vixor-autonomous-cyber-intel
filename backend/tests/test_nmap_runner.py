"""Unit tests for Nmap runner (T-026).

Tests use mocks since the nmap binary is not available locally.
Covers:
- Valid hostname runs nmap with safe flags (shell=False, allowlisted args)
- JSON output parsed into scan data
- Missing binary returns error dict
- Timeout returns error dict
- Non-zero exit returns error dict
- JSON parse error handled gracefully
- Invalid/empty hostname returns error dict
"""

from unittest.mock import MagicMock, patch

from app.services.scanning.nmap_runner import run_nmap


class TestRunNmap:
    """Tests for run_nmap."""

    @patch("app.services.scanning.nmap_runner.subprocess.run")
    def test_valid_hostname_runs_nmap(self, mock_run):
        """Valid hostname triggers nmap with safe, allowlisted args."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"scan": {}}'
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = run_nmap("example.com")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "nmap"
        assert "-sV" in args
        assert "--script" in args
        assert "safe" in args
        assert "-oJ" in args
        assert "-" in args
        assert "-T4" in args
        assert "--max-retries" in args
        assert "--host-timeout" in args
        assert "example.com" in args
        # shell=False by design: args is a list, no string interpolation
        assert isinstance(args, list)
        assert result["host"] == "example.com"
        assert "scan_data" in result

    @patch("app.services.scanning.nmap_runner.subprocess.run")
    def test_json_output_parsed(self, mock_run):
        """JSON output from nmap is parsed into scan_data."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = (
            '{"scan": {"example.com": {"tcp": {"80": {"state": "open", '
            '"name": "http", "product": "nginx", "version": "1.2.3"}}}}}'
        )
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = run_nmap("example.com")

        assert result["host"] == "example.com"
        assert (
            result["scan_data"]["scan"]["example.com"]["tcp"]["80"]["state"] == "open"
        )

    @patch("app.services.scanning.nmap_runner.subprocess.run")
    def test_nmap_not_found(self, mock_run):
        """Missing nmap binary returns error dict."""
        mock_run.side_effect = FileNotFoundError("nmap not found")

        result = run_nmap("example.com")

        assert result["host"] == "example.com"
        assert result["error"] == "nmap not installed"

    @patch("app.services.scanning.nmap_runner.subprocess.run")
    def test_nmap_timeout(self, mock_run):
        """Timeout returns error dict."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("nmap", 300)

        result = run_nmap("example.com")

        assert result["host"] == "example.com"
        assert result["error"] == "timeout"

    @patch("app.services.scanning.nmap_runner.subprocess.run")
    def test_nmap_failure(self, mock_run):
        """Non-zero exit returns error dict."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "connection refused"
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        result = run_nmap("example.com")

        assert result["host"] == "example.com"
        assert result["error"] == "connection refused"

    @patch("app.services.scanning.nmap_runner.subprocess.run")
    def test_json_parse_error(self, mock_run):
        """JSON parse error returns parse_error with raw output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not json"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = run_nmap("example.com")

        assert result["host"] == "example.com"
        assert result["error"] == "parse_error"
        assert result["raw"] == "not json"

    def test_invalid_hostname(self):
        """Invalid hostname returns error dict."""
        result = run_nmap("not a hostname")

        assert result["host"] == "not a hostname"
        assert "error" in result

    def test_empty_hostname(self):
        """Empty hostname returns error dict."""
        result = run_nmap("")

        assert result["host"] == ""
        assert "error" in result
