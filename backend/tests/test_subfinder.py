"""Unit tests for Subfinder runner (T-021).

Tests use mocks since the subfinder binary is not available locally.
Covers:
- Valid domain runs subfinder with correct arguments
- Invalid domain raises ValueError
- Missing binary raises RuntimeError
- Timeout raises RuntimeError
- Non-zero exit raises RuntimeError
- JSON output parsing
- Plain hostname output parsing
- Scope filtering
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.discovery.subfinder import filter_subdomains_by_scope, run_subfinder


class TestRunSubfinder:
    """Tests for the run_subfinder function."""

    @patch("app.services.discovery.subfinder.subprocess.run")
    def test_valid_domain_runs_subfinder(self, mock_run):
        """Valid domain triggers subfinder with correct args."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = run_subfinder("example.com")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "subfinder"
        assert "-d" in args
        assert "example.com" in args
        assert "-silent" in args
        assert "-json" in args
        assert "-timeout" in args
        assert result == []

    @patch("app.services.discovery.subfinder.subprocess.run")
    def test_json_output_parsed(self, mock_run):
        """JSON lines from subfinder are parsed into hostnames."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = (
            '{"host": "sub1.example.com"}\n{"host": "sub2.example.com"}'
        )
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = run_subfinder("example.com")

        assert "sub1.example.com" in result
        assert "sub2.example.com" in result
        assert len(result) == 2

    @patch("app.services.discovery.subfinder.subprocess.run")
    def test_root_domain_excluded(self, mock_run):
        """The root domain itself is excluded from results."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"host": "example.com"}'
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = run_subfinder("example.com")

        assert result == []

    @patch("app.services.discovery.subfinder.subprocess.run")
    def test_plain_hostname_parsed(self, mock_run):
        """Plain hostname lines (non-JSON) are parsed."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "sub1.example.com\nsub2.example.com\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = run_subfinder("example.com")

        assert "sub1.example.com" in result
        assert "sub2.example.com" in result

    @patch("app.services.discovery.subfinder.subprocess.run")
    def test_subfinder_not_found(self, mock_run):
        """Missing subfinder binary raises RuntimeError."""
        mock_run.side_effect = FileNotFoundError("subfinder not found")

        with pytest.raises(RuntimeError, match="subfinder binary not installed"):
            run_subfinder("example.com")

    @patch("app.services.discovery.subfinder.subprocess.run")
    def test_subfinder_timeout(self, mock_run):
        """Subfinder timeout raises RuntimeError."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("subfinder", 300)

        with pytest.raises(RuntimeError, match="timed out"):
            run_subfinder("example.com")

    @patch("app.services.discovery.subfinder.subprocess.run")
    def test_subfinder_failure(self, mock_run):
        """Non-zero exit code raises RuntimeError."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "some error"
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        with pytest.raises(RuntimeError, match="subfinder failed"):
            run_subfinder("example.com")

    def test_invalid_domain_raises_value_error(self):
        """Invalid domain format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid domain"):
            run_subfinder("not a hostname")

    def test_empty_domain_raises_value_error(self):
        """Empty domain raises ValueError."""
        with pytest.raises(ValueError, match="Invalid domain"):
            run_subfinder("")


class TestFilterSubdomainsByScope:
    """Tests for the filter_subdomains_by_scope function."""

    def test_exact_domain_in_scope(self):
        """The root domain itself is in scope."""
        result = filter_subdomains_by_scope(["example.com"], "example.com")
        assert result == ["example.com"]

    def test_subdomain_in_scope(self):
        """Subdomains of the root domain are in scope."""
        result = filter_subdomains_by_scope(
            ["sub.example.com", "a.b.example.com"], "example.com"
        )
        assert "sub.example.com" in result
        assert "a.b.example.com" in result

    def test_unrelated_domain_out_of_scope(self):
        """Unrelated domains are out of scope."""
        result = filter_subdomains_by_scope(
            ["evil.com", "example.com.evil.com"], "example.com"
        )
        assert "evil.com" not in result
        assert "example.com.evil.com" not in result

    def test_empty_list(self):
        """Empty list returns empty list."""
        result = filter_subdomains_by_scope([], "example.com")
        assert result == []
