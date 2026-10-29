"""Unit tests for Nuclei runner (T-028).

Tests use mocks since the nuclei binary is not available locally.
Covers:
- Valid target runs nuclei with excluded tags (dos, intrusive, fuzz, bruteforce)
- JSONL output parsed into list of findings
- Missing binary returns error dict
- Timeout returns error dict
- Non-zero exit returns error dict
- JSONL parse errors skipped gracefully
- Invalid/empty target returns error dict
- shell=False by design (argument list, no shell interpolation)
"""

from unittest.mock import MagicMock, patch

from app.services.scanning.nuclei_runner import NUCLEI_EXCLUDED_TAGS, run_nuclei


class TestRunNuclei:
    """Tests for run_nuclei."""

    @patch("app.services.scanning.nuclei_runner.subprocess.run")
    def test_valid_target_runs_nuclei(self, mock_run):
        """Valid target triggers nuclei with excluded tags and allowlisted args."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = run_nuclei("https://example.com")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "nuclei"
        assert "-u" in args
        assert "https://example.com" in args
        assert "-jsonl" in args
        assert "-silent" in args
        assert "-timeout" in args
        assert "-retries" in args
        assert "-exclude-tags" in args
        assert NUCLEI_EXCLUDED_TAGS == "dos,intrusive,fuzz,bruteforce"
        assert "dos" in NUCLEI_EXCLUDED_TAGS
        assert "intrusive" in NUCLEI_EXCLUDED_TAGS
        assert "fuzz" in NUCLEI_EXCLUDED_TAGS
        assert "bruteforce" in NUCLEI_EXCLUDED_TAGS
        # shell=False: args is a list, no shell interpolation of user input
        assert isinstance(args, list)
        assert result == []

    @patch("app.services.scanning.nuclei_runner.subprocess.run")
    def test_jsonl_output_parsed(self, mock_run):
        """JSONL output from nuclei is parsed into finding dicts."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = (
            '{"template-id": "http-exposure", "info": {"name": "Exposure", '
            '"severity": "medium", "description": "Endpoint exposed", '
            '"cvss_score": 6.1, "cve": ["CVE-2021-0001"]}, '
            '"matched-at": "https://example.com/.env"}\n'
            '{"template-id": "http-misconfig", "info": {"name": "Misconfig", '
            '"severity": "low", "description": "Misconfigured header"}, '
            '"matched-at": "https://example.com/"}\n'
        )
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = run_nuclei("https://example.com")

        assert len(result) == 2
        assert result[0]["template-id"] == "http-exposure"
        assert result[0]["info"]["name"] == "Exposure"
        assert result[0]["info"]["severity"] == "medium"
        assert result[0]["matched-at"] == "https://example.com/.env"
        assert result[1]["template-id"] == "http-misconfig"

    @patch("app.services.scanning.nuclei_runner.subprocess.run")
    def test_nuclei_not_found(self, mock_run):
        """Missing nuclei binary returns error dict."""
        mock_run.side_effect = FileNotFoundError("nuclei not found")

        result = run_nuclei("https://example.com")

        assert len(result) == 1
        assert result[0]["target"] == "https://example.com"
        assert result[0]["error"] == "nuclei not installed"

    @patch("app.services.scanning.nuclei_runner.subprocess.run")
    def test_nuclei_timeout(self, mock_run):
        """Timeout returns error dict."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("nuclei", 300)

        result = run_nuclei("https://example.com")

        assert len(result) == 1
        assert result[0]["target"] == "https://example.com"
        assert result[0]["error"] == "timeout"

    @patch("app.services.scanning.nuclei_runner.subprocess.run")
    def test_nuclei_failure(self, mock_run):
        """Non-zero exit returns error dict."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "connection refused"
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        result = run_nuclei("https://example.com")

        assert len(result) == 1
        assert result[0]["target"] == "https://example.com"
        assert result[0]["error"] == "connection refused"

    @patch("app.services.scanning.nuclei_runner.subprocess.run")
    def test_jsonl_parse_error_skipped(self, mock_run):
        """Invalid JSONL lines are skipped, valid ones parsed."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not json\n"
        mock_result.stdout += (
            '{"template-id": "valid", "info": {"name": "Valid", "severity": "info"}}\n'
        )
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = run_nuclei("https://example.com")

        assert len(result) == 1
        assert result[0]["template-id"] == "valid"

    def test_invalid_target(self):
        """Invalid target returns error dict."""
        result = run_nuclei("not a hostname")

        assert len(result) == 1
        assert result[0]["target"] == "not a hostname"
        assert "error" in result[0]

    def test_empty_target(self):
        """Empty target returns error dict."""
        result = run_nuclei("")

        assert len(result) == 1
        assert result[0]["target"] == ""
        assert "error" in result[0]
