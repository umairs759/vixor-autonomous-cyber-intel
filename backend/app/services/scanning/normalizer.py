"""VIXOR — Finding normalizer (T-026 to T-028).

Converts scanner-specific output into a unified Finding schema.
Deduplication by fingerprint is handled separately.
"""

import hashlib
from typing import Any

from app.core.logging import get_logger

logger = get_logger("scanning.normalizer")


def compute_fingerprint(
    source_tool: str,
    title: str,
    hostname: str,
    port: Optional[int] = None,
) -> str:
    """Compute a deterministic fingerprint for a finding.

    Used for deduplication across tools and scan cycles.
    """
    parts = [source_tool, title, hostname]
    if port is not None:
        parts.append(str(port))
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()


def normalize_nmap(
    scan_data: dict,
    hostname: str,
) -> list[dict]:
    """Normalize Nmap output into unified findings.

    Args:
        scan_data: Raw Nmap JSON output.
        hostname: Target hostname.

    Returns:
        List of normalized findings.
    """
    findings: list[dict] = []

    # Nmap JSON structure varies; extract port/service info
    host_data = scan_data.get("scan", {}).get(hostname, {})
    ports = host_data.get("tcp", {}) or host_data.get("udp", {})

    for port, info in ports.items():
        state = info.get("state", "")
        if state != "open":
            continue

        service = info.get("name", "unknown")
        product = info.get("product", "")
        version = info.get("version", "")
        title = f"{service} service on port {port}"
        if product:
            title += f" ({product}"
            if version:
                title += f" {version}"
            title += ")"

        fingerprint = compute_fingerprint("nmap", title, hostname, int(port))

        findings.append({
            "fingerprint": fingerprint,
            "source_tool": "nmap",
            "title": title,
            "description": f"Port {port}/{info.get('protocol', 'tcp')} is open running {service}.",
            "severity_raw": "info",
            "cvss": None,
            "cve_ids": [],
            "evidence": {
                "port": int(port),
                "protocol": info.get("protocol", "tcp"),
                "service": service,
                "product": product,
                "version": version,
                "extrainfo": info.get("extrainfo", ""),
            },
            "remediation": "Review if this service is required and properly secured.",
        })

    return findings


def normalize_zap(
    zap_alerts: list[dict],
    hostname: str,
) -> list[dict]:
    """Normalize ZAP alert output into unified findings."""
    findings: list[dict] = []

    for alert in zap_alerts:
        title = alert.get("alert", "ZAP finding")
        fingerprint = compute_fingerprint("zap", title, hostname)

        findings.append({
            "fingerprint": fingerprint,
            "source_tool": "zap",
            "title": title,
            "description": alert.get("description", ""),
            "severity_raw": alert.get("risk", "info").lower(),
            "cvss": None,
            "cve_ids": [],
            "evidence": {
                "url": alert.get("url", ""),
                "param": alert.get("param", ""),
                "attack": alert.get("attack", ""),
                "evidence": alert.get("evidence", ""),
                "reference": alert.get("reference", ""),
                "cwe_id": alert.get("cweid", ""),
                "wasc_id": alert.get("wascid", ""),
            },
            "remediation": alert.get("solution", "Review and remediate according to best practices."),
        })

    return findings


def normalize_nuclei(
    nuclei_results: list[dict],
    hostname: str,
) -> list[dict]:
    """Normalize Nuclei JSONL output into unified findings."""
    findings: list[dict] = []

    for result in nuclei_results:
        template_id = result.get("template-id", "unknown")
        name = result.get("info", {}).get("name", "Nuclei finding")
        severity = result.get("info", {}).get("severity", "info").lower()
        title = f"{name} ({template_id})"
        fingerprint = compute_fingerprint("nuclei", title, hostname)

        findings.append({
            "fingerprint": fingerprint,
            "source_tool": "nuclei",
            "title": title,
            "description": result.get("info", {}).get("description", ""),
            "severity_raw": severity,
            "cvss": result.get("info", {}).get("cvss_score"),
            "cve_ids": result.get("info", {}).get("cve", []),
            "evidence": {
                "matched_at": result.get("matched-at", ""),
                "template": template_id,
                "extracted_results": result.get("extracted-results", []),
            },
            "remediation": result.get("info", {}).get("remediation", "Review and remediate according to best practices."),
        })

    return findings
