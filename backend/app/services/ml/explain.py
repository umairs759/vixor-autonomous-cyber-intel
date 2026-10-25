"""VIXOR — SHAP explanations + narrative generator (T-036).

Deterministic template-based narratives generated from SHAP values.
No LLMs are used for scoring or narratives.
"""

from typing import Any

from app.core.logging import get_logger

logger = get_logger("ml.explain")


# Narrative templates mapped to feature names
NARRATIVE_TEMPLATES = {
    "cvss_base": "CVSS base score of {cvss} indicates {severity} severity",
    "in_cisa_kev": "this CVE is listed in CISA KEV ({kev_contribution})",
    "epss_score": "EPSS score of {epss} indicates {epss_desc} exploitation likelihood",
    "exploit_available": "public exploit is available ({exploit_contribution})",
    "asset_sensitivity": "asset hosts sensitive functionality ({sensitivity_contribution})",
    "internet_exposed": "asset is internet-exposed ({internet_contribution})",
    "auth_required": "authentication is required ({auth_contribution})",
    "service_port_risk": "service runs on a high-risk port ({port_contribution})",
    "tool_confidence": "scanner confidence is {confidence}",
    "template_severity": "scanner template severity is {sev}",
    "age_of_cve_days": "CVE is {age} days old ({age_contribution})",
    "recurrence_count": "finding has recurred {count} times ({recurrence_contribution})",
    "detected_tech_outdated": "detected technology is outdated ({tech_contribution})",
}


def generate_narrative(
    risk_score: float,
    shap_values: dict[str, float],
    features: dict[str, Any],
    top_n: int = 5,
) -> str:
    """Generate a deterministic natural-language risk narrative from SHAP values.

    Args:
        risk_score: The overall risk score (0-100).
        shap_values: SHAP feature contributions.
        features: The input features used for scoring.
        top_n: Number of top SHAP drivers to include.

    Returns:
        A narrative sentence explaining the risk score.
    """
    if not shap_values:
        return f"Risk score is {risk_score:.0f}/100 based on available factors."

    # Sort SHAP values by absolute magnitude (top drivers)
    sorted_shap = sorted(
        shap_values.items(),
        key=lambda x: abs(x[1]),
        reverse=True,
    )
    top_drivers = sorted_shap[:top_n]

    # Build narrative from top drivers
    parts: list[str] = []
    for feature_name, contribution in top_drivers:
        if abs(contribution) < 0.1:
            continue

        direction = "increases" if contribution > 0 else "decreases"
        feature_display = feature_name.replace("_", " ")

        # Get feature value for context
        feat_val = features.get(feature_name, "N/A")
        if isinstance(feat_val, bool):
            feat_val = "yes" if feat_val else "no"

        template = NARRATIVE_TEMPLATES.get(feature_name, "{feature} {direction}")
        try:
            part = template.format(
                feature=feature_display,
                direction=direction,
                contribution=abs(contribution),
                cvss=features.get("cvss_base", 0) * 10,
                kev_contribution=abs(contribution),
                epss=features.get("epss_score", 0),
                epss_desc="high" if features.get("epss_score", 0) > 0.5 else "low",
                exploit_contribution=abs(contribution),
                sensitivity_contribution=abs(contribution),
                internet_contribution=abs(contribution),
                auth_contribution=abs(contribution),
                port_contribution=abs(contribution),
                confidence=feat_val,
                sev=feat_val,
                age=int(features.get("age_of_cve_days", 0) * 3650),
                age_contribution=abs(contribution),
                count=int(features.get("recurrence_count", 0) * 10),
                recurrence_contribution=abs(contribution),
                tech_contribution=abs(contribution),
            )
        except (KeyError, ValueError):
            part = f"{feature_display} {direction} risk ({abs(contribution):.1f})"

        parts.append(part)

    if not parts:
        return f"Risk score is {risk_score:.0f}/100."

    # Combine into narrative
    if len(parts) == 1:
        narrative = f"Risk is {risk_score:.0f}/100 mainly because {parts[0]}."
    elif len(parts) == 2:
        narrative = (
            f"Risk is {risk_score:.0f}/100 mainly because {parts[0]} and {parts[1]}."
        )
    else:
        narrative = (
            f"Risk is {risk_score:.0f}/100 mainly because "
            f"{', '.join(parts[:-1])}, and {parts[-1]}."
        )

    return narrative


def get_top_shap_drivers(
    shap_values: dict[str, float],
    top_n: int = 5,
) -> list[tuple[str, float]]:
    """Get the top N SHAP drivers by absolute magnitude."""
    sorted_shap = sorted(
        shap_values.items(),
        key=lambda x: abs(x[1]),
        reverse=True,
    )
    return sorted_shap[:top_n]
