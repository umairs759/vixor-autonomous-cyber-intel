"""VIXOR — Nmap runner (T-026).

Runs Nmap with safe flags only (-sV for service detection, safe scripts).
No exploit scripts. Uses subprocess with shell=False and allowlisted args.
"""

import json
import subprocess
from typing import Optional

from app.core.logging import get_logger
from app.services.scope_guard import validate_hostname

logger = get_logger("scanning.nmap")


def run_nmap(
    hostname: str,
    timeout_seconds: int = 300,
) -> dict:
    """Run Nmap service detection on a host.

    Security:
    - -sV for service version detection only
    - Safe scripts only (default safe category)
    - No exploit scripts
    - subprocess with shell=False, allowlisted args
    - Per-tool timeout enforced

    Returns:
        Dict with scan results including open ports, services, versions.
    """
    valid, reason = validate_hostname(hostname)
    if not valid:
        return {"error": reason, "host": hostname}

    cmd = [
        "nmap",
        "-sV",
        "--script", "safe",
        "-oJ", "-",  # JSON output to stdout
        "-T4",
        "--max-retries", "2",
        "--host-timeout", f"{timeout_seconds}s",
        hostname,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 30,
            check=False,
        )
    except FileNotFoundError:
        logger.error("nmap binary not found")
        return {"error": "nmap not installed", "host": hostname}
    except subprocess.TimeoutExpired:
        logger.warning("nmap timeout", hostname=hostname)
        return {"error": "timeout", "host": hostname}

    if result.returncode != 0:
        return {
            "error": result.stderr[:200],
            "host": hostname,
        }

    try:
        data = json.loads(result.stdout)
        return {
            "host": hostname,
            "scan_data": data,
        }
    except json.JSONDecodeError:
        return {
            "host": hostname,
            "error": "parse_error",
            "raw": result.stdout[:500],
        }
