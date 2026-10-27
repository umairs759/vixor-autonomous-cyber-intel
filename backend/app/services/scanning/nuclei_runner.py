"""VIXOR — Nuclei runner (T-028).

Runs Nuclei with excluded tags (dos, intrusive, fuzz, bruteforce).
Uses subprocess with shell=False and allowlisted arguments.
JSONL output parsing.
"""

import json
import subprocess
from typing import Any
from urllib.parse import urlparse

from app.core.logging import get_logger
from app.services.scope_guard import validate_hostname

logger = get_logger("scanning.nuclei")

# Nuclei excluded tags per LI-2 / BO-10
NUCLEI_EXCLUDED_TAGS = "dos,intrusive,fuzz,bruteforce"


def run_nuclei(
    target_url: str,
    timeout_seconds: int = 300,
) -> list[dict[str, Any]]:
    """Run Nuclei with safe templates only.

    Security:
    - Excludes tags: dos, intrusive, fuzz, bruteforce
    - subprocess with shell=False, allowlisted args
    - JSONL output parsing
    - Per-tool timeout enforced
    - Target URL validated before scanning

    Returns:
        List of findings from Nuclei.
    """
    parsed = urlparse(target_url)
    hostname = parsed.hostname or ""

    valid, reason = validate_hostname(hostname)
    if not valid:
        return [{"error": reason, "target": target_url}]

    cmd = [
        "nuclei",
        "-u",
        target_url,
        "-jsonl",
        "-silent",
        "-timeout",
        str(timeout_seconds),
        "-retries",
        "1",
        "-exclude-tags",
        NUCLEI_EXCLUDED_TAGS,
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
        logger.error("nuclei binary not found")
        return [{"error": "nuclei not installed", "target": target_url}]
    except subprocess.TimeoutExpired:
        logger.warning("nuclei timeout", target=target_url)
        return [{"error": "timeout", "target": target_url}]

    if result.returncode != 0:
        return [
            {
                "error": result.stderr[:200],
                "target": target_url,
            }
        ]

    findings: list[dict[str, Any]] = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        try:
            finding = json.loads(line)
            findings.append(finding)
        except json.JSONDecodeError:
            logger.warning("nuclei jsonl parse error", line=line[:100])

    logger.info(
        "nuclei completed",
        target=target_url,
        findings_found=len(findings),
    )
    return findings
