"""VIXOR — Feature extraction service (T-034).

Extracts ML features from findings for risk scoring.
"""

from typing import Any

from app.core.logging import get_logger

logger = get_logger("ml.features")


def extract_features(
    finding: dict[str, Any],
    finding_score: dict[str, Any] | None = None,
    asset_sensitivity: float = 0.5,
    recurrence_count: int = 0,
    is_in_cisa_kev: bool = False,
    epss_score: float = 0.0,
    cvss_base: float = 0.0,
    age_of_cve_days: int = 0,
    detected_tech_outdated: bool = False,
    exploit_available: bool = False,
    internet_exposed: bool = True,
    auth_required: bool = False,
    tool_confidence: float = 0.8,
    template_severity: str = "medium",
) -> dict[str, Any]:
    """Extract ML features from a finding for risk scoring.

    Features documented in ARCHITECTURE.md section 5:
    - cvss_base, epss_score, in_cisa_kev, exploit_available
    - asset_sensitivity, internet_exposed, auth_required
    - service_port_risk, tool_confidence, template_severity
    - age_of_cve_days, recurrence_count, detected_tech_outdated

    Returns a dict of feature names to numeric values.
    """
    # Service port risk mapping
    port_risk_map: dict[str, float] = {
        "21": 0.6,  # FTP
        "22": 0.3,  # SSH
        "23": 0.8,  # Telnet
        "25": 0.5,  # SMTP
        "53": 0.4,  # DNS
        "80": 0.4,  # HTTP
        "110": 0.5,  # POP3
        "443": 0.5,  # HTTPS
        "3389": 0.7,  # RDP
        "5432": 0.6,  # PostgreSQL
        "3306": 0.6,  # MySQL
        "6379": 0.7,  # Redis
        "27017": 0.7,  # MongoDB
    }

    evidence = finding.get("evidence", {}) if isinstance(finding, dict) else {}
    if not evidence and isinstance(finding, dict) and "port" in finding:
        evidence = finding

    port = str(evidence.get("port", "0"))

    # Derive CVSS from finding when not explicitly provided
    if cvss_base == 0.0 and isinstance(finding, dict):
        raw_cvss = finding.get("cvss")
        if raw_cvss is not None:
            try:
                cvss_base = float(raw_cvss)
            except (TypeError, ValueError):
                cvss_base = 0.0

    # Derive template severity from finding when not explicitly provided
    if template_severity == "medium" and isinstance(finding, dict):
        raw_severity = finding.get("severity_raw")
        if raw_severity:
            template_severity = str(raw_severity)

    # Template severity to numeric
    severity_map: dict[str, float] = {
        "low": 0.25,
        "medium": 0.5,
        "high": 0.75,
        "critical": 1.0,
        "info": 0.1,
    }
    template_sev_val = severity_map.get(template_severity.lower(), 0.5)

    # Internet exposure heuristic from finding
    if internet_exposed is True and isinstance(finding, dict):
        # default remains True unless finding explicitly says otherwise
        pass

    features: dict[str, Any] = {
        "cvss_base": float(cvss_base) / 10.0,  # Normalize to 0-1
        "epss_score": float(epss_score),
        "in_cisa_kev": 1.0 if is_in_cisa_kev else 0.0,
        "exploit_available": 1.0 if exploit_available else 0.0,
        "asset_sensitivity": float(asset_sensitivity),
        "internet_exposed": 1.0 if internet_exposed else 0.0,
        "auth_required": 1.0 if auth_required else 0.0,
        "service_port_risk": float(port_risk_map.get(port, 0.3)),
        "tool_confidence": float(tool_confidence),
        "template_severity": template_sev_val,
        "age_of_cve_days": float(min(age_of_cve_days, 3650)) / 3650.0,
        "recurrence_count": float(min(recurrence_count, 10)) / 10.0,
        "detected_tech_outdated": 1.0 if detected_tech_outdated else 0.0,
    }

    return features


def feature_names() -> list[str]:
    """Return the ordered list of feature names used by the model."""
    return [
        "cvss_base",
        "epss_score",
        "in_cisa_kev",
        "exploit_available",
        "asset_sensitivity",
        "internet_exposed",
        "auth_required",
        "service_port_risk",
        "tool_confidence",
        "template_severity",
        "age_of_cve_days",
        "recurrence_count",
        "detected_tech_outdated",
    ]
