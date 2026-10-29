"""Unit tests for finding normalizer (T-026 to T-028).

Covers:
- compute_fingerprint is deterministic and includes port when provided
- normalize_nmap extracts open ports with service/product/version
- normalize_nmap skips closed ports
- normalize_zap converts alerts to unified findings
- normalize_nuclei converts JSONL results to unified findings
- Fingerprints are stable across calls (dedupe-friendly)
"""

from app.services.scanning.normalizer import (
    compute_fingerprint,
    normalize_nmap,
    normalize_nuclei,
    normalize_zap,
)


class TestComputeFingerprint:
    """Tests for compute_fingerprint."""

    def test_deterministic(self):
        """Same inputs always produce the same fingerprint."""
        a = compute_fingerprint("nmap", "http service on port 80", "example.com", 80)
        b = compute_fingerprint("nmap", "http service on port 80", "example.com", 80)
        assert a == b
        assert len(a) == 64  # sha256 hex

    def test_includes_port(self):
        """Fingerprint differs when port is provided vs omitted."""
        with_port = compute_fingerprint("nmap", "http", "example.com", 80)
        without_port = compute_fingerprint("nmap", "http", "example.com")
        assert with_port != without_port

    def test_different_inputs_differ(self):
        """Different titles produce different fingerprints."""
        a = compute_fingerprint("nmap", "http", "example.com", 80)
        b = compute_fingerprint("nmap", "https", "example.com", 80)
        assert a != b


class TestNormalizeNmap:
    """Tests for normalize_nmap."""

    def test_extracts_open_ports(self):
        """Open TCP ports are converted to findings with service info."""
        scan_data = {
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
                        },
                        "443": {
                            "state": "open",
                            "name": "https",
                            "product": "",
                            "version": "",
                            "extrainfo": "",
                            "protocol": "tcp",
                        },
                    }
                }
            }
        }

        findings = normalize_nmap(scan_data, "example.com")

        assert len(findings) == 2
        titles = {f["title"] for f in findings}
        assert "http service on port 80 (nginx 1.2.3)" in titles
        assert "https service on port 443" in titles
        for f in findings:
            assert f["source_tool"] == "nmap"
            assert f["severity_raw"] == "info"
            assert "port" in f["evidence"]
            assert f["evidence"]["service"] in ("http", "https")

    def test_skips_closed_ports(self):
        """Closed or filtered ports are not converted to findings."""
        scan_data = {
            "scan": {
                "example.com": {
                    "tcp": {
                        "80": {"state": "open", "name": "http"},
                        "22": {"state": "closed", "name": "ssh"},
                        "8080": {"state": "filtered", "name": "http-proxy"},
                    }
                }
            }
        }

        findings = normalize_nmap(scan_data, "example.com")

        assert len(findings) == 1
        assert findings[0]["evidence"]["port"] == 80

    def test_empty_scan_data(self):
        """Empty scan data returns no findings."""
        assert normalize_nmap({}, "example.com") == []
        assert normalize_nmap({"scan": {}}, "example.com") == []


class TestNormalizeZap:
    """Tests for normalize_zap."""

    def test_converts_alerts(self):
        """ZAP alerts are converted to unified findings."""
        alerts = [
            {
                "alert": "XSS",
                "description": "Reflected XSS found",
                "risk": "high",
                "url": "https://example.com/search?q=test",
                "param": "q",
                "attack": "<script>alert(1)</script>",
                "evidence": "script tag reflected",
                "reference": "https://owasp.org/",
                "cweid": "79",
                "wascid": "8",
                "solution": "Encode user input.",
            }
        ]

        findings = normalize_zap(alerts, "example.com")

        assert len(findings) == 1
        f = findings[0]
        assert f["source_tool"] == "zap"
        assert f["title"] == "XSS"
        assert f["severity_raw"] == "high"
        assert f["evidence"]["cwe_id"] == "79"
        assert f["evidence"]["url"] == "https://example.com/search?q=test"
        assert f["remediation"] == "Encode user input."

    def test_empty_alerts(self):
        """Empty alert list returns no findings."""
        assert normalize_zap([], "example.com") == []


class TestNormalizeNuclei:
    """Tests for normalize_nuclei."""

    def test_converts_results(self):
        """Nuclei JSONL results are converted to unified findings."""
        results = [
            {
                "template-id": "http-exposure",
                "info": {
                    "name": "Exposure",
                    "severity": "medium",
                    "description": "Endpoint exposed",
                    "cvss_score": 6.1,
                    "cve": ["CVE-2021-0001"],
                    "remediation": "Restrict access.",
                },
                "matched-at": "https://example.com/.env",
                "extracted-results": [".env"],
            }
        ]

        findings = normalize_nuclei(results, "example.com")

        assert len(findings) == 1
        f = findings[0]
        assert f["source_tool"] == "nuclei"
        assert f["title"] == "Exposure (http-exposure)"
        assert f["severity_raw"] == "medium"
        assert f["cvss"] == 6.1
        assert f["cve_ids"] == ["CVE-2021-0001"]
        assert f["evidence"]["matched_at"] == "https://example.com/.env"
        assert f["remediation"] == "Restrict access."

    def test_empty_results(self):
        """Empty results list returns no findings."""
        assert normalize_nuclei([], "example.com") == []
