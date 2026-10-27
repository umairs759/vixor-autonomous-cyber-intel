"""VIXOR — DNS enumeration + wildcard detection (T-023).

Performs DNS A record resolution for subdomains and detects wildcard DNS.
"""

from typing import Any

import dns.resolver

from app.core.logging import get_logger
from app.services.scope_guard import validate_hostname

logger = get_logger("discovery.dns_enum")


def resolve_a_records(hostname: str) -> list[str]:
    """Resolve A records for a hostname.

    Returns list of IP addresses. Empty list on failure.
    """
    valid, _reason = validate_hostname(hostname)
    if not valid:
        return []

    try:
        answers = dns.resolver.resolve(hostname, "A")
        return [str(answer) for answer in answers]
    except Exception:  # noqa: BLE001 - DNS resolution failures are expected
        return []


def detect_wildcard(domain: str) -> bool:
    """Detect if a domain has wildcard DNS.

    Queries a random non-existent subdomain. If it resolves, the domain
    likely has wildcard DNS.
    """
    import random
    import string

    random_label = "".join(random.choice(string.ascii_lowercase) for _ in range(16))
    test_host = f"{random_label}.{domain}"
    ips = resolve_a_records(test_host)
    return len(ips) > 0


def enumerate_dns(domain: str, subdomains: list[str]) -> dict[str, list[str]]:
    """Resolve A records for a list of subdomains.

    Returns mapping of hostname -> list of IPs.
    Wildcard DNS is detected and reported separately.
    """
    results: dict[str, Any] = {}
    wildcard = detect_wildcard(domain)

    for sub in subdomains:
        ips = resolve_a_records(sub)
        if ips:
            results[sub] = ips

    results["_wildcard_detected"] = wildcard
    return results
