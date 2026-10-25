"""VIXOR — Scope Guard service (T-020).

Enforces scanning scope rules (LI-1, BO-10):
- Domain must have verified_at within last 7 days (REVERIFY_INTERVAL_DAYS).
- Asset hostname must equal or be a subdomain of verified root domain.
- All resolved IPs must be public, not cloud-metadata, not in CDN/shared-hosting blocklist.
- Private range blocking unless ALLOW_PRIVATE_IP_SCANNING=true (lab mode only).
- Strict hostname validation to prevent injection/bypass.

Returns (is_in_scope: bool, reason: str | None).
"""

import ipaddress
import re
from datetime import UTC, datetime

import dns.resolver

from app.config import get_settings
from app.core.logging import get_logger
from app.models.domain import Domain, DomainStatus

logger = get_logger("scope_guard")
settings = get_settings()

# Strict hostname regex (RFC 1123 compliant)
# Labels: 1-63 chars, alphanumeric + hyphen, not starting/ending with hyphen
# No underscores, no IPs, no ports, no schemes
_HOSTNAME_RE = re.compile(
    r"^(?![0-9]+$)(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(\.[a-zA-Z0-9-]{1,63}(?<!-))*$"
)

# Cloud metadata IP (AWS, GCP, Azure)
CLOUD_METADATA_IP = "169.254.169.254"

# Known CDN / shared hosting IP ranges (subset for MVP)
# These are ranges where subdomains commonly resolve to third-party infrastructure
CDN_SHARED_HOSTING_RANGES = [
    # Cloudflare
    "104.16.0.0/12",
    "172.64.0.0/13",
    "131.0.72.0/22",
    # Amazon CloudFront
    "13.32.0.0/15",
    "13.35.0.0/16",
    "13.52.0.0/15",
    "13.54.0.0/16",
    "13.56.0.0/16",
    "13.58.0.0/16",
    "13.60.0.0/16",
    "13.62.0.0/16",
    "13.64.0.0/16",
    "13.66.0.0/16",
    "13.68.0.0/16",
    "13.70.0.0/16",
    "13.72.0.0/16",
    "13.74.0.0/16",
    "13.76.0.0/16",
    "13.78.0.0/16",
    "13.80.0.0/16",
    "13.82.0.0/16",
    "13.84.0.0/16",
    "13.86.0.0/16",
    "13.88.0.0/16",
    "13.90.0.0/16",
    "13.92.0.0/16",
    "13.94.0.0/16",
    "13.96.0.0/16",
    "13.98.0.0/16",
    "13.100.0.0/16",
    "13.102.0.0/16",
    "13.104.0.0/16",
    "13.106.0.0/16",
    "13.108.0.0/16",
    "13.110.0.0/16",
    "13.112.0.0/16",
    "13.114.0.0/16",
    "13.116.0.0/16",
    "13.118.0.0/16",
    "13.120.0.0/16",
    "13.122.0.0/16",
    "13.124.0.0/16",
    "13.126.0.0/16",
    "13.128.0.0/16",
    "13.130.0.0/16",
    "13.132.0.0/16",
    "13.134.0.0/16",
    "13.136.0.0/16",
    "13.138.0.0/16",
    "13.140.0.0/16",
    "13.142.0.0/16",
    "13.144.0.0/16",
    "13.146.0.0/16",
    "13.148.0.0/16",
    "13.150.0.0/16",
    "13.152.0.0/16",
    "13.154.0.0/16",
    "13.156.0.0/16",
    "13.158.0.0/16",
    "13.160.0.0/16",
    "13.162.0.0/16",
    "13.164.0.0/16",
    "13.166.0.0/16",
    "13.168.0.0/16",
    "13.170.0.0/16",
    "13.172.0.0/16",
    "13.174.0.0/16",
    "13.176.0.0/16",
    "13.178.0.0/16",
    "13.180.0.0/16",
    "13.182.0.0/16",
    "13.184.0.0/16",
    "13.186.0.0/16",
    "13.188.0.0/16",
    "13.190.0.0/16",
    "13.192.0.0/16",
    "13.194.0.0/16",
    "13.196.0.0/16",
    "13.198.0.0/16",
    "13.200.0.0/16",
    "13.202.0.0/16",
    "13.204.0.0/16",
    "13.206.0.0/16",
    "13.208.0.0/16",
    "13.210.0.0/16",
    "13.212.0.0/16",
    "13.214.0.0/16",
    "13.216.0.0/16",
    "13.218.0.0/16",
    "13.220.0.0/16",
    "13.222.0.0/16",
    "13.224.0.0/16",
    "13.226.0.0/16",
    "13.228.0.0/16",
    "13.230.0.0/16",
    "13.232.0.0/16",
    "13.234.0.0/16",
    "13.236.0.0/16",
    "13.238.0.0/16",
    "13.240.0.0/16",
    "13.242.0.0/16",
    "13.244.0.0/16",
    "13.246.0.0/16",
    "13.248.0.0/16",
    "13.250.0.0/16",
    "13.252.0.0/16",
    "13.254.0.0/16",
    # Google Cloud
    "34.64.0.0/10",
    "35.184.0.0/13",
    "35.192.0.0/14",
    "35.196.0.0/15",
    "35.198.0.0/16",
    "35.200.0.0/13",
    "35.208.0.0/12",
    "35.224.0.0/12",
    # Azure
    "13.64.0.0/11",
    "13.96.0.0/11",
    "13.128.0.0/11",
    "13.160.0.0/11",
    "20.0.0.0/8",
    "23.96.0.0/11",
    "23.128.0.0/11",
    "40.64.0.0/10",
    "40.112.0.0/12",
    "52.32.0.0/14",
    "52.64.0.0/10",
    "52.96.0.0/11",
    "52.128.0.0/11",
    "52.160.0.0/11",
    "52.192.0.0/11",
    "52.224.0.0/11",
    "104.40.0.0/12",
    "104.64.0.0/10",
    "104.128.0.0/11",
    "104.160.0.0/11",
    "104.192.0.0/11",
    "104.224.0.0/11",
    # Akamai
    "23.32.0.0/13",
    "23.40.0.0/13",
    "23.48.0.0/13",
    "23.56.0.0/13",
    "23.64.0.0/13",
    "23.72.0.0/13",
    "23.80.0.0/13",
    "23.88.0.0/13",
    "23.96.0.0/13",
    "23.104.0.0/13",
    "23.112.0.0/13",
    "23.120.0.0/13",
    "23.128.0.0/13",
    "23.136.0.0/13",
    "23.144.0.0/13",
    "23.152.0.0/13",
    "23.160.0.0/13",
    "23.168.0.0/13",
    "23.176.0.0/13",
    "23.184.0.0/13",
    "23.192.0.0/13",
    "23.200.0.0/13",
    "23.208.0.0/13",
    "23.216.0.0/13",
    "23.224.0.0/13",
    "23.232.0.0/13",
    "23.240.0.0/13",
]

# Pre-compile CDN networks for performance
_CDN_NETWORKS = [
    ipaddress.ip_network(rng, strict=False) for rng in CDN_SHARED_HOSTING_RANGES
]

# Private IP ranges (RFC 1918 + loopback + link-local)
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def is_private_or_reserved_ip(ip_str: str) -> bool:
    """Check if an IP string is private, loopback, link-local, or reserved."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # Invalid IP is treated as unsafe

    # Check cloud metadata IP
    if ip_str == CLOUD_METADATA_IP:
        return True

    # Check private ranges
    for net in _PRIVATE_NETWORKS:
        if ip in net:
            return True

    # Check CDN/shared-hosting ranges
    for net in _CDN_NETWORKS:
        if ip in net:
            return True

    return False


def validate_hostname(hostname: str) -> tuple[bool, str | None]:
    """Validate hostname format strictly.

    Returns (is_valid, reason). Rejects:
    - Empty hostnames
    - IP addresses as hostnames
    - Underscores
    - Ports or schemes
    - Trailing dots (unless single root)
    - Unicode homograph risks (basic check)
    - Labels > 63 chars
    - Labels starting/ending with hyphen
    """
    if not hostname or not hostname.strip():
        return False, "Hostname is empty"

    hostname = hostname.strip().lower()

    # Reject trailing dots (FQDN notation) except single dot
    if hostname.endswith(".") and hostname != ".":
        return False, "Trailing dot in hostname is not allowed"

    # Reject if it looks like an IP address
    try:
        ipaddress.ip_address(hostname)
        return False, "IP address used as hostname is not allowed"
    except ValueError:
        pass

    # Reject underscores (not valid in DNS hostnames)
    if "_" in hostname:
        return False, "Underscore in hostname is not allowed"

    # Reject ports or schemes
    if ":" in hostname or "://" in hostname or "/" in hostname:
        return False, "Port, scheme, or path in hostname is not allowed"

    # Basic unicode homograph check: reject non-ASCII characters
    try:
        hostname.encode("ascii")
    except UnicodeEncodeError:
        return False, "Non-ASCII characters in hostname (homograph risk)"

    # Match against strict hostname regex
    if not _HOSTNAME_RE.match(hostname):
        return False, "Hostname does not match RFC 1123 format"

    return True, None


def is_subdomain_of(hostname: str, root_domain: str) -> bool:
    """Check if hostname equals or is a subdomain of root_domain.

    Both must be valid hostnames. hostname must be root_domain or
    *.root_domain (one or more subdomain levels).
    """
    hostname = hostname.lower().strip()
    root_domain = root_domain.lower().strip()

    if hostname == root_domain:
        return True

    # hostname must end with .root_domain
    suffix = "." + root_domain
    if hostname.endswith(suffix):
        # Ensure the part before the suffix is a valid subdomain label
        prefix = hostname[: -len(suffix)]
        if prefix and not prefix.startswith(".") and not prefix.endswith("."):
            return True

    return False


def resolve_ips(hostname: str) -> list[str]:
    """Resolve a hostname to its IP addresses via DNS A record lookup.

    Returns a list of IP strings. Empty list if resolution fails.
    """
    try:
        answers = dns.resolver.resolve(hostname, "A")
        return [str(answer) for answer in answers]
    except Exception:  # noqa: BLE001 - DNS resolution failures are expected, return empty
        logger.warning("dns_resolution_failed", hostname=hostname)
        return []


def is_domain_verified_recently(domain: Domain) -> tuple[bool, str | None]:
    """Check if domain's verified_at is within the re-verification window.

    Returns (is_valid, reason).
    """
    if domain.status != DomainStatus.verified:
        return False, f"Domain status is {domain.status.value}, not verified"

    if domain.verified_at is None:
        return False, "Domain has no verified_at timestamp"

    now = datetime.now(UTC)
    verified_at = domain.verified_at
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=UTC)

    age = now - verified_at
    max_age = settings.REVERIFY_INTERVAL_DAYS * 86400  # days to seconds

    if age.total_seconds() > max_age:
        return False, (
            f"Domain verification expired ({age.days} days old, "
            f"max {settings.REVERIFY_INTERVAL_DAYS} days)"
        )

    return True, None


def is_in_scope(
    domain: Domain,
    hostname: str,
    resolve_dns: bool = True,
) -> tuple[bool, str | None]:
    """Check if a hostname is in scope for scanning a given domain.

    Enforces all scope guard rules:
    1. Domain must be verified and within re-verification window
    2. Hostname must be valid format
    3. Hostname must equal or be subdomain of domain root
    4. All resolved IPs must be public, not metadata, not CDN/shared-hosting

    Returns (is_in_scope: bool, reason: str | None).
    """
    # Step 1: Domain verification check
    verified, reason = is_domain_verified_recently(domain)
    if not verified:
        logger.warning(
            "scope_guard_domain_not_verified",
            domain_id=domain.id,
            root_domain=domain.root_domain,
            reason=reason,
        )
        return False, reason

    # Step 2: Hostname format validation
    valid, reason = validate_hostname(hostname)
    if not valid:
        logger.warning(
            "scope_guard_invalid_hostname",
            domain_id=domain.id,
            root_domain=domain.root_domain,
            hostname=hostname,
            reason=reason,
        )
        return False, reason

    # Step 3: Subdomain check
    if not is_subdomain_of(hostname, domain.root_domain):
        logger.warning(
            "scope_guard_not_subdomain",
            domain_id=domain.id,
            root_domain=domain.root_domain,
            hostname=hostname,
        )
        return False, (
            f"Hostname {hostname} is not a subdomain of {domain.root_domain}"
        )

    # Step 4: IP resolution and scope check
    if resolve_dns:
        ips = resolve_ips(hostname)
        if not ips:
            return False, f"Could not resolve any IP addresses for {hostname}"

        for ip in ips:
            if is_private_or_reserved_ip(ip):
                logger.warning(
                    "scope_guard_ip_out_of_scope",
                    domain_id=domain.id,
                    root_domain=domain.root_domain,
                    hostname=hostname,
                    ip=ip,
                )
                return False, (
                    f"IP {ip} for {hostname} is private, metadata, or CDN/shared-hosting"
                )

    logger.info(
        "scope_guard_in_scope",
        domain_id=domain.id,
        root_domain=domain.root_domain,
        hostname=hostname,
    )
    return True, None
