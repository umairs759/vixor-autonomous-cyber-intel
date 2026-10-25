"""VIXOR — Subfinder runner (T-021).

Runs subfinder to discover subdomains for a given domain.
Uses subprocess with shell=False and allowlisted arguments only.
Never interpolates user input into shell commands.
"""

import json
import subprocess
from typing import Optional

from app.core.logging import get_logger
from app.services.scope_guard import is_in_scope, validate_hostname

logger = get_logger("discovery.subfinder")


def run_subfinder(
    domain: str,
    timeout_seconds: int = 300,
) -> list[str]:
    """Run subfinder to enumerate subdomains.

    Args:
        domain: The root domain to enumerate (validated before calling).
        timeout_seconds: Per-tool timeout.

    Returns:
        List of discovered subdomains (excluding the root domain itself).

    Raises:
        ValueError: If the domain is invalid.
        RuntimeError: If subfinder fails.
    """
    # Validate domain format
    valid, reason = validate_hostname(domain)
    if not valid:
        raise ValueError(f"Invalid domain: {reason}")

    # Build allowlisted argument list - no shell interpolation
    cmd = [
        "subfinder",
        "-d", domain,
        "-silent",
        "-json",
        "-timeout", str(timeout_seconds),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        logger.error("subfinder binary not found")
        raise RuntimeError("subfinder binary not installed")
    except subprocess.TimeoutExpired:
        logger.warning("subfinder timeout", domain=domain, timeout=timeout_seconds)
        raise RuntimeError(f"subfinder timed out after {timeout_seconds}s")

    if result.returncode != 0:
        logger.error(
            "subfinder failed",
            domain=domain,
            returncode=result.returncode,
            stderr=result.stderr[:500],
        )
        raise RuntimeError(f"subfinder failed: {result.stderr[:200]}")

    subdomains: list[str] = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        try:
            entry = json.loads(line)
            host = entry.get("host", "")
            if host and host != domain:
                subdomains.append(host)
        except json.JSONDecodeError:
            # Try parsing as plain hostname
            host = line.strip()
            if host and host != domain:
                subdomains.append(host)

    logger.info(
        "subfinder completed",
        domain=domain,
        subdomains_found=len(subdomains),
    )
    return subdomains


def filter_subdomains_by_scope(
    subdomains: list[str],
    domain: str,
) -> list[str]:
    """Filter discovered subdomains to only those within scope.

    A subdomain is in scope if it equals or is a subdomain of the root domain.
    """
    return [s for s in subdomains if s.endswith("." + domain) or s == domain]
