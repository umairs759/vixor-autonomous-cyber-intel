"""VIXOR — httpx probe (T-024).

Probes hosts for liveness and technology fingerprinting using httpx.
Uses subprocess with shell=False and allowlisted arguments.
"""

import json
import subprocess
from typing import Any

from app.core.logging import get_logger
from app.services.scope_guard import validate_hostname

logger = get_logger("discovery.httpx")


def probe_host(
    hostname: str,
    timeout_seconds: int = 10,
) -> dict[str, Any]:
    """Run httpx to check if a host is live and detect technologies.

    Args:
        hostname: Target hostname.
        timeout_seconds: Per-tool timeout.

    Returns:
        Dict with 'live', 'status_code', 'title', 'technologies', 'url'.
    """
    valid, reason = validate_hostname(hostname)
    if not valid:
        return {"live": False, "error": reason}

    cmd = [
        "httpx",
        "-u",
        f"https://{hostname}",
        "-silent",
        "-json",
        "-timeout",
        str(timeout_seconds),
        "-title",
        "-td",  # technology detection
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 10,
            check=False,
        )
    except FileNotFoundError:
        logger.error("httpx binary not found")
        return {"live": False, "error": "httpx not installed"}
    except subprocess.TimeoutExpired:
        logger.warning("httpx timeout", hostname=hostname)
        return {"live": False, "error": "timeout"}

    if result.returncode != 0:
        return {"live": False, "error": result.stderr[:200]}

    try:
        data = json.loads(result.stdout.strip())
        return {
            "live": True,
            "status_code": data.get("status_code"),
            "title": data.get("title"),
            "technologies": data.get("technologies", []),
            "url": data.get("url"),
        }
    except json.JSONDecodeError:
        return {"live": True, "error": "parse_error"}
