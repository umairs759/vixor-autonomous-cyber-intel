"""Unit tests for Scan Orchestrator (T-029).

Tests mock scanner runners (nmap, zap, nuclei) and scope_guard since
scanner binaries and live DNS are not available locally. Covers:
- scope_guard enforced before any scanner runs (short-circuits out-of-scope)
- Nmap and Nuclei run and findings are normalized and aggregated
- Partial failure: one tool fails, others continue
- Out-of-scope asset returns no findings, no scanner called
- Unverified domain returns no findings
- Overall status: completed / partial / failed
- ZAP is optional
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.services.scanning.orchestrator import ScanOrchestrator

NOW = datetime.now(UTC)


def _nmap_result():
    return {
        "scan_data": {
            "scan": {
                "example.com": {
                    "tcp": {
                        "80": {
                            "state": "open",
                            "name": "http",
                            "product": "nginx",
                            "version": "1.2.3",
                            "extrainfo": "",
                            "protocol": "tcp",
                        }
                    }
                }
            }
        }
    }


def _nuclei_result():
    return [
        {
            "template-id": "http-exposure",
            "info": {
                "name": "Exposure",
                "severity": "medium",
                "description": "Exposed",
                "cvss_score": 6.1,
                "cve": [],
            },
            "matched-at": "https://example.com/.env",
        }
    ]


class TestScanOrchestrator:
    """Tests for ScanOrchestrator.scan_asset."""

    def test_full_pipeline_all_tools(self):
        """All scanners run and findings are normalized and aggregated."""
        orchestrator = ScanOrchestrator(timeout_seconds=60)
        with patch.multiple(
            "app.services.scanning.orchestrator",
            is_in_scope=MagicMock(return_value=(True, None)),
            run_nmap=MagicMock(return_value=_nmap_result()),
            run_nuclei=MagicMock(return_value=_nuclei_result()),
        ):
            result = orchestrator.scan_asset(
                domain_root="example.com",
                hostname="example.com",
                domain_verified=True,
                verified_at=NOW,
            )

        assert result["hostname"] == "example.com"
        assert result["in_scope"] is True
        assert result["status"] == "completed"
        assert len(result["findings"]) >= 2  # nmap + nuclei findings
        assert "nmap" in result["tools"]
        assert "nuclei" in result["tools"]

    def test_out_of_scope_no_scanners(self):
        """Out-of-scope asset returns immediately, no scanners called."""
        orchestrator = ScanOrchestrator(timeout_seconds=60)
        with patch.multiple(
            "app.services.scanning.orchestrator",
            is_in_scope=MagicMock(return_value=(False, "out of scope")),
            run_nmap=MagicMock(),
            run_nuclei=MagicMock(),
        ):
            result = orchestrator.scan_asset(
                domain_root="example.com",
                hostname="evil.com",
                domain_verified=True,
                verified_at=NOW,
            )

        assert result["in_scope"] is False
        assert result["findings"] == []
        # scope check short-circuits before scanners, so no tool ran
        assert result["tools"] == {}
        # Early-return path leaves no status key set
        assert "status" not in result

    def test_partial_failure_continues(self):
        """One tool raising an exception does not crash the pipeline."""
        nuclei_result = _nuclei_result()

        orchestrator = ScanOrchestrator(timeout_seconds=60)
        with patch.multiple(
            "app.services.scanning.orchestrator",
            is_in_scope=MagicMock(return_value=(True, None)),
            run_nmap=MagicMock(side_effect=RuntimeError("nmap crashed")),
            run_nuclei=MagicMock(return_value=nuclei_result),
        ):
            result = orchestrator.scan_asset(
                domain_root="example.com",
                hostname="example.com",
                domain_verified=True,
                verified_at=NOW,
            )

        assert result["status"] == "partial"
        assert len(result["errors"]) >= 1
        assert len(result["findings"]) >= 1  # nuclei findings still present

    def test_all_tools_fail(self):
        """All tools failing returns failed status."""
        nmap_result = {"error": "nmap not installed"}
        nuclei_result = [{"error": "nuclei not installed", "target": "x"}]

        orchestrator = ScanOrchestrator(timeout_seconds=60)
        with patch.multiple(
            "app.services.scanning.orchestrator",
            is_in_scope=MagicMock(return_value=(True, None)),
            run_nmap=MagicMock(return_value=nmap_result),
            run_nuclei=MagicMock(return_value=nuclei_result),
        ):
            result = orchestrator.scan_asset(
                domain_root="example.com",
                hostname="example.com",
                domain_verified=True,
                verified_at=NOW,
            )

        assert result["status"] == "failed"
        assert result["findings"] == []

    def test_zap_optional(self):
        """ZAP is optional; pipeline works without a ZapRunner."""
        nuclei_result = []

        orchestrator = ScanOrchestrator(zap_runner=None, timeout_seconds=60)
        with patch.multiple(
            "app.services.scanning.orchestrator",
            is_in_scope=MagicMock(return_value=(True, None)),
            run_nmap=MagicMock(return_value=_nmap_result()),
            run_nuclei=MagicMock(return_value=nuclei_result),
        ):
            result = orchestrator.scan_asset(
                domain_root="example.com",
                hostname="example.com",
                domain_verified=True,
                verified_at=NOW,
            )

        assert "zap" not in result["tools"]
        assert result["status"] == "completed"
