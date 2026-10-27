"""Unit tests for DNS enumeration + wildcard detection (T-023).

Tests use mocked dns.resolver since DNS queries are not performed locally.
Covers:
- A record resolution returns IPs
- DNS resolution failure returns empty list
- Invalid hostname returns empty list
- Wildcard detection returns True when random subdomain resolves
- Wildcard detection returns False when random subdomain doesn't resolve
- DNS enumeration resolves A records for multiple subdomains
- Wildcard flag included in enumeration results
"""

from unittest.mock import MagicMock, patch

from app.services.discovery.dns_enum import (
    detect_wildcard,
    enumerate_dns,
    resolve_a_records,
)


class TestResolveARecords:
    """Tests for resolve_a_records."""

    @patch("app.services.discovery.dns_enum.dns.resolver.resolve")
    def test_valid_hostname_returns_ips(self, mock_resolve):
        """Valid hostname returns list of IP addresses."""
        mock_answer = MagicMock()
        mock_answer.__str__ = MagicMock(return_value="93.184.216.34")
        mock_resolve.return_value = [mock_answer]

        result = resolve_a_records("example.com")

        assert "93.184.216.34" in result
        mock_resolve.assert_called_once_with("example.com", "A")

    @patch("app.services.discovery.dns_enum.dns.resolver.resolve")
    def test_multiple_ips_returned(self, mock_resolve):
        """Multiple A records all returned."""
        mock_answer1 = MagicMock()
        mock_answer1.__str__ = MagicMock(return_value="1.2.3.4")
        mock_answer2 = MagicMock()
        mock_answer2.__str__ = MagicMock(return_value="5.6.7.8")
        mock_resolve.return_value = [mock_answer1, mock_answer2]

        result = resolve_a_records("example.com")

        assert len(result) == 2
        assert "1.2.3.4" in result
        assert "5.6.7.8" in result

    @patch("app.services.discovery.dns_enum.dns.resolver.resolve")
    def test_resolution_failure_returns_empty(self, mock_resolve):
        """DNS resolution failure returns empty list."""
        mock_resolve.side_effect = Exception("NXDOMAIN")

        result = resolve_a_records("nonexistent.example.com")

        assert result == []

    def test_invalid_hostname_returns_empty(self):
        """Invalid hostname returns empty list."""
        result = resolve_a_records("not a hostname")

        assert result == []

    def test_empty_hostname_returns_empty(self):
        """Empty hostname returns empty list."""
        result = resolve_a_records("")

        assert result == []


class TestDetectWildcard:
    """Tests for detect_wildcard."""

    @patch("app.services.discovery.dns_enum.resolve_a_records")
    def test_wildcard_detected(self, mock_resolve):
        """Wildcard detected when random subdomain resolves."""
        mock_resolve.return_value = ["1.2.3.4"]

        result = detect_wildcard("example.com")

        assert result is True
        mock_resolve.assert_called_once()
        # Verify the queried host is a subdomain of example.com
        called_host = mock_resolve.call_args[0][0]
        assert called_host.endswith(".example.com")

    @patch("app.services.discovery.dns_enum.resolve_a_records")
    def test_wildcard_not_detected(self, mock_resolve):
        """No wildcard when random subdomain doesn't resolve."""
        mock_resolve.return_value = []

        result = detect_wildcard("example.com")

        assert result is False

    @patch("app.services.discovery.dns_enum.resolve_a_records")
    def test_wildcard_random_label_length(self, mock_resolve):
        """Random label is 16 characters."""
        mock_resolve.return_value = []

        detect_wildcard("example.com")

        called_host = mock_resolve.call_args[0][0]
        label = called_host.split(".")[0]
        assert len(label) == 16


class TestEnumerateDNS:
    """Tests for enumerate_dns."""

    @patch("app.services.discovery.dns_enum.resolve_a_records")
    @patch("app.services.discovery.dns_enum.detect_wildcard")
    def test_enumeration_resolves_subdomains(self, mock_detect_wildcard, mock_resolve):
        """DNS enumeration resolves A records for each subdomain."""
        mock_detect_wildcard.return_value = False

        def resolve_side_effect(hostname):
            if hostname == "sub1.example.com":
                return ["1.2.3.4"]
            if hostname == "sub2.example.com":
                return ["5.6.7.8"]
            return []

        mock_resolve.side_effect = resolve_side_effect

        result = enumerate_dns("example.com", ["sub1.example.com", "sub2.example.com"])

        assert "sub1.example.com" in result
        assert "sub2.example.com" in result
        assert result["sub1.example.com"] == ["1.2.3.4"]
        assert result["sub2.example.com"] == ["5.6.7.8"]

    @patch("app.services.discovery.dns_enum.resolve_a_records")
    @patch("app.services.discovery.dns_enum.detect_wildcard")
    def test_wildcard_flag_in_results(self, mock_detect_wildcard, mock_resolve):
        """Wildcard detection flag is included in results."""
        mock_detect_wildcard.return_value = True
        mock_resolve.return_value = []

        result = enumerate_dns("example.com", ["sub.example.com"])

        assert result.get("_wildcard_detected") is True

    @patch("app.services.discovery.dns_enum.resolve_a_records")
    @patch("app.services.discovery.dns_enum.detect_wildcard")
    def test_empty_subdomains_list(self, mock_detect_wildcard, mock_resolve):
        """Empty subdomain list returns only wildcard flag."""
        mock_detect_wildcard.return_value = False
        mock_resolve.return_value = []

        result = enumerate_dns("example.com", [])

        assert result.get("_wildcard_detected") is False
        assert len(result) == 1  # only _wildcard_detected key
