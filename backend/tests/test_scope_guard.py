"""Unit tests for scope_guard service (T-020).

Tests cover:
- Hostname validation (adversarial: evil.com?.victim.com, trailing dots,
  unicode homographs, IPs as hostnames)
- Subdomain checking
- IP resolution and private/CDN/metadata blocking
- Domain verification window
- Full is_in_scope flow
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from app.models.domain import Domain, DomainStatus, VerificationMethod
from app.services.scope_guard import (
    is_domain_verified_recently,
    is_in_scope,
    is_private_or_reserved_ip,
    is_subdomain_of,
    resolve_ips,
    validate_hostname,
)


class TestValidateHostname:
    """Tests for strict hostname validation."""

    def test_valid_hostname(self):
        assert validate_hostname("example.com") == (True, None)
        assert validate_hostname("sub.example.com") == (True, None)
        assert validate_hostname("a.b.c.d.example.com") == (True, None)
        assert validate_hostname("my-site.example.com") == (True, None)

    def test_empty_hostname(self):
        valid, reason = validate_hostname("")
        assert not valid
        assert "empty" in reason.lower()

    def test_ip_as_hostname(self):
        valid, reason = validate_hostname("192.168.1.1")
        assert not valid
        assert "ip" in reason.lower()

        valid, reason = validate_hostname("10.0.0.1")
        assert not valid

        valid, reason = validate_hostname("8.8.8.8")
        assert not valid

    def test_underscore_in_hostname(self):
        valid, reason = validate_hostname("my_host.example.com")
        assert not valid
        assert "underscore" in reason.lower()

    def test_port_in_hostname(self):
        valid, _reason = validate_hostname("example.com:8080")
        assert not valid

    def test_scheme_in_hostname(self):
        valid, _reason = validate_hostname("https://example.com")
        assert not valid

    def test_path_in_hostname(self):
        valid, _reason = validate_hostname("example.com/path")
        assert not valid

    def test_trailing_dot(self):
        valid, reason = validate_hostname("example.com.")
        assert not valid
        assert "trailing" in reason.lower()

    def test_unicode_homograph(self):
        # Non-ASCII characters (homograph risk)
        valid, reason = validate_hostname("exаmple.com")  # Cyrillic 'a'
        assert not valid
        assert "non-ascii" in reason.lower() or "homograph" in reason.lower()

    def test_adversarial_subdomain_injection(self):
        # evil.com?.victim.com - the '?' should be rejected by regex
        valid, _reason = validate_hostname("evil.com?.victim.com")
        assert not valid

    def test_label_too_long(self):
        # Label > 63 chars
        long_label = "a" * 64
        valid, _reason = validate_hostname(f"{long_label}.com")
        assert not valid

    def test_label_starts_with_hyphen(self):
        valid, _reason = validate_hostname("-example.com")
        assert not valid

    def test_label_ends_with_hyphen(self):
        valid, _reason = validate_hostname("example-.com")
        assert not valid

    def test_all_numeric_label(self):
        # "123.example.com" is a valid hostname format per RFC 1123
        valid, _reason = validate_hostname("123.example.com")
        assert valid

    def test_entirely_numeric_hostname_rejected(self):
        # A hostname that is entirely numeric is rejected (could be IP fragment)
        valid, _reason = validate_hostname("12345")
        assert not valid

    def test_double_dot(self):
        valid, _reason = validate_hostname("ex..ample.com")
        assert not valid

    def test_leading_dot(self):
        valid, _reason = validate_hostname(".example.com")
        assert not valid

    def test_single_character_domain(self):
        valid, _reason = validate_hostname("a.com")
        assert valid


class TestIsSubdomainOf:
    """Tests for subdomain relationship checking."""

    def test_exact_match(self):
        assert is_subdomain_of("example.com", "example.com")

    def test_single_subdomain(self):
        assert is_subdomain_of("sub.example.com", "example.com")

    def test_multi_level_subdomain(self):
        assert is_subdomain_of("a.b.example.com", "example.com")

    def test_not_subdomain(self):
        assert not is_subdomain_of("evil.com", "example.com")
        assert not is_subdomain_of("example.com.evil.com", "example.com")
        assert not is_subdomain_of("notexample.com", "example.com")

    def test_case_insensitive(self):
        assert is_subdomain_of("SUB.EXAMPLE.COM", "example.com")


class TestIsPrivateOrReservedIp:
    """Tests for IP range blocking."""

    def test_private_rfc1918(self):
        assert is_private_or_reserved_ip("10.0.0.1")
        assert is_private_or_reserved_ip("172.16.0.1")
        assert is_private_or_reserved_ip("192.168.1.1")

    def test_loopback(self):
        assert is_private_or_reserved_ip("127.0.0.1")
        assert is_private_or_reserved_ip("127.0.0.53")

    def test_link_local(self):
        assert is_private_or_reserved_ip("169.254.1.1")

    def test_cloud_metadata(self):
        assert is_private_or_reserved_ip("169.254.169.254")

    def test_public_ip(self):
        assert not is_private_or_reserved_ip("8.8.8.8")
        assert not is_private_or_reserved_ip("1.1.1.1")
        assert not is_private_or_reserved_ip("93.184.216.34")

    def test_invalid_ip(self):
        assert is_private_or_reserved_ip("not.an.ip")
        assert is_private_or_reserved_ip("999.999.999.999")

    def test_ipv6_loopback(self):
        assert is_private_or_reserved_ip("::1")

    def test_ipv6_private(self):
        assert is_private_or_reserved_ip("fc00::1")


class TestResolveIps:
    """Tests for DNS resolution (mocked)."""

    @patch("app.services.scope_guard.dns.resolver.resolve")
    def test_successful_resolution(self, mock_resolve):
        mock_answer = MagicMock()
        mock_answer.__str__ = lambda self: "93.184.216.34"
        mock_resolve.return_value = [mock_answer]
        ips = resolve_ips("example.com")
        assert "93.184.216.34" in ips

    @patch("app.services.scope_guard.dns.resolver.resolve")
    def test_resolution_failure(self, mock_resolve):
        mock_resolve.side_effect = Exception("NXDOMAIN")
        ips = resolve_ips("nonexistent.example.com")
        assert ips == []

    @patch("app.services.scope_guard.dns.resolver.resolve")
    def test_multiple_ips(self, mock_resolve):
        mock_resolve.return_value = [
            MagicMock(str=lambda self: "1.2.3.4"),
            MagicMock(str=lambda self: "5.6.7.8"),
        ]
        ips = resolve_ips("example.com")
        assert len(ips) == 2


class TestIsDomainVerifiedRecently:
    """Tests for domain verification window check."""

    def test_verified_within_window(self):
        domain = Domain(
            id="test-id",
            project_id="proj-id",
            root_domain="example.com",
            verification_token="token",
            verification_method=VerificationMethod.dns_txt,
            status=DomainStatus.verified,
            verified_at=datetime.now(UTC) - timedelta(hours=1),
        )
        valid, reason = is_domain_verified_recently(domain)
        assert valid
        assert reason is None

    def test_not_verified(self):
        domain = Domain(
            id="test-id",
            project_id="proj-id",
            root_domain="example.com",
            verification_token="token",
            verification_method=VerificationMethod.dns_txt,
            status=DomainStatus.unverified,
        )
        valid, reason = is_domain_verified_recently(domain)
        assert not valid
        assert "not verified" in reason.lower()

    def test_verified_expired(self):
        domain = Domain(
            id="test-id",
            project_id="proj-id",
            root_domain="example.com",
            verification_token="token",
            verification_method=VerificationMethod.dns_txt,
            status=DomainStatus.verified,
            verified_at=datetime.now(UTC) - timedelta(days=10),
        )
        valid, reason = is_domain_verified_recently(domain)
        assert not valid
        assert "expired" in reason.lower() or "days" in reason.lower()

    def test_no_verified_at(self):
        domain = Domain(
            id="test-id",
            project_id="proj-id",
            root_domain="example.com",
            verification_token="token",
            verification_method=VerificationMethod.dns_txt,
            status=DomainStatus.verified,
            verified_at=None,
        )
        valid, reason = is_domain_verified_recently(domain)
        assert not valid
        assert "no verified_at" in reason.lower()


class TestIsInScope:
    """Full integration tests for is_in_scope."""

    def _make_domain(
        self,
        status: DomainStatus = DomainStatus.verified,
        verified_days_ago: float = 1.0,
        root_domain: str = "example.com",
    ) -> Domain:
        verified_at = None
        if status == DomainStatus.verified:
            verified_at = datetime.now(UTC) - timedelta(days=verified_days_ago)
        return Domain(
            id="domain-id",
            project_id="proj-id",
            root_domain=root_domain,
            verification_token="token",
            verification_method=VerificationMethod.dns_txt,
            status=status,
            verified_at=verified_at,
        )

    @patch("app.services.scope_guard.resolve_ips")
    def test_in_scope_valid_subdomain(self, mock_resolve):
        mock_resolve.return_value = ["93.184.216.34"]  # Public IP
        domain = self._make_domain()
        valid, reason = is_in_scope(domain, "sub.example.com")
        assert valid
        assert reason is None

    @patch("app.services.scope_guard.resolve_ips")
    def test_in_scope_exact_domain(self, mock_resolve):
        mock_resolve.return_value = ["93.184.216.34"]
        domain = self._make_domain()
        valid, _reason = is_in_scope(domain, "example.com")
        assert valid

    @patch("app.services.scope_guard.resolve_ips")
    def test_out_of_scope_different_domain(self, mock_resolve):
        mock_resolve.return_value = ["93.184.216.34"]
        domain = self._make_domain(root_domain="example.com")
        valid, reason = is_in_scope(domain, "evil.com")
        assert not valid
        assert "subdomain" in reason.lower()

    @patch("app.services.scope_guard.resolve_ips")
    def test_out_of_scope_domain_suffix_attack(self, mock_resolve):
        # example.com.evil.com should NOT be in scope of example.com
        mock_resolve.return_value = ["93.184.216.34"]
        domain = self._make_domain(root_domain="example.com")
        valid, reason = is_in_scope(domain, "example.com.evil.com")
        assert not valid
        assert "subdomain" in reason.lower()

    @patch("app.services.scope_guard.resolve_ips")
    def test_out_of_scope_private_ip(self, mock_resolve):
        mock_resolve.return_value = ["192.168.1.1"]
        domain = self._make_domain()
        valid, reason = is_in_scope(domain, "internal.example.com")
        assert not valid
        assert "private" in reason.lower() or "ip" in reason.lower()

    @patch("app.services.scope_guard.resolve_ips")
    def test_out_of_scope_cloud_metadata(self, mock_resolve):
        mock_resolve.return_value = ["169.254.169.254"]
        domain = self._make_domain()
        valid, _reason = is_in_scope(domain, "metadata.example.com")
        assert not valid

    @patch("app.services.scope_guard.resolve_ips")
    def test_out_of_scope_unverified_domain(self, mock_resolve):
        domain = self._make_domain(status=DomainStatus.unverified)
        valid, reason = is_in_scope(domain, "sub.example.com")
        assert not valid
        assert "not verified" in reason.lower()

    @patch("app.services.scope_guard.resolve_ips")
    def test_out_of_scope_expired_verification(self, mock_resolve):
        domain = self._make_domain(verified_days_ago=10.0)
        valid, reason = is_in_scope(domain, "sub.example.com")
        assert not valid
        assert "expired" in reason.lower()

    @patch("app.services.scope_guard.resolve_ips")
    def test_out_of_scope_invalid_hostname(self, mock_resolve):
        domain = self._make_domain()
        valid, _reason = is_in_scope(domain, "not a hostname")
        assert not valid

    @patch("app.services.scope_guard.resolve_ips")
    def test_out_of_scope_ip_as_hostname(self, mock_resolve):
        domain = self._make_domain()
        valid, _reason = is_in_scope(domain, "192.168.1.1")
        assert not valid

    @patch("app.services.scope_guard.resolve_ips")
    def test_no_ips_resolved(self, mock_resolve):
        mock_resolve.return_value = []
        domain = self._make_domain()
        valid, reason = is_in_scope(domain, "sub.example.com")
        assert not valid
        assert "resolve" in reason.lower()

    @patch("app.services.scope_guard.resolve_ips")
    def test_cdn_ip_blocked(self, mock_resolve):
        # Cloudflare IP
        mock_resolve.return_value = ["104.16.0.1"]
        domain = self._make_domain()
        valid, reason = is_in_scope(domain, "cdn.example.com")
        assert not valid
        assert "cdn" in reason.lower() or "ip" in reason.lower()

    @patch("app.services.scope_guard.resolve_ips")
    def test_mixed_ips_one_private(self, mock_resolve):
        # One public, one private - should fail
        mock_resolve.return_value = ["93.184.216.34", "10.0.0.1"]
        domain = self._make_domain()
        valid, _reason = is_in_scope(domain, "multi.example.com")
        assert not valid
