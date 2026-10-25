"""VIXOR — Correlation engine (T-038).

Rule-based grouping of related findings into attack narratives.
Combines scores for correlated findings.
"""

from typing import Any

from app.core.logging import get_logger
from app.models.finding import Finding

logger = get_logger("ml.correlation")


class CorrelationEngine:
    """Groups related findings into correlated attack narratives."""

    def __init__(self, db_session):
        self.db = db_session

    def correlate_findings(
        self,
        scan_id: str,
        asset_id: str,
    ) -> list[dict]:
        """Group findings for an asset into correlated narratives.

        Rules:
        - Multiple findings on the same port/service -> grouped
        - Multiple web-related findings (XSS, missing headers, etc.) -> grouped
        - High-severity findings combined -> higher combined score

        Returns:
            List of correlation groups with narratives and combined scores.
        """
        findings = (
            self.db.query(Finding)
            .filter(Finding.scan_id == scan_id, Finding.asset_id == asset_id)
            .all()
        )

        if not findings:
            return []

        # Group findings by similarity rules
        groups = self._group_findings(findings)

        correlations: list[dict] = []
        for group in groups:
            if len(group) < 2:
                continue  # Single findings don't need correlation

            combined_score = self._compute_combined_score(group)
            narrative = self._generate_narrative(group, combined_score)
            finding_ids = [f.id for f in group]

            correlations.append(
                {
                    "scan_id": scan_id,
                    "asset_id": asset_id,
                    "title": group[0].title,
                    "narrative": narrative,
                    "combined_score": combined_score,
                    "finding_ids": finding_ids,
                }
            )

        return correlations

    def _group_findings(
        self,
        findings: list[Any],
    ) -> list[list[Any]]:
        """Group findings by similarity rules."""
        groups: list[list[Any]] = []
        used: set[str] = set()

        # Rule 1: Group by same port
        port_groups: dict[str, list[Any]] = {}
        for f in findings:
            if f.id in used:
                continue
            port = f.evidence.get("port", "unknown") if f.evidence else "unknown"
            key = f"port:{port}"
            if key not in port_groups:
                port_groups[key] = []
            port_groups[key].append(f)
            used.add(f.id)

        for group in port_groups.values():
            if len(group) >= 2:
                groups.append(group)

        # Rule 2: Group web-related findings
        web_keywords = ["xss", "header", "cookie", "csrf", "clickjacking"]
        web_findings: list[Any] = []
        for f in findings:
            if f.id in used:
                continue
            text = f"{f.title} {f.description}".lower()
            if any(kw in text for kw in web_keywords):
                web_findings.append(f)
                used.add(f.id)

        if len(web_findings) >= 2:
            groups.append(web_findings)

        # Rule 3: Group high-severity findings
        high_findings: list[Any] = []
        for f in findings:
            if f.id in used:
                continue
            if f.severity_raw.lower() in ("high", "critical"):
                high_findings.append(f)
                used.add(f.id)

        if len(high_findings) >= 2:
            groups.append(high_findings)

        return groups

    def _compute_combined_score(
        self,
        findings: list[Any],
    ) -> float:
        """Compute combined score from correlated findings.

        Uses the maximum individual score as base, with a boost
        for multiple findings (indicating a broader attack surface).
        """
        scores: list[float] = []
        for f in findings:
            # Use CVSS or severity as base
            if f.cvss:
                scores.append(f.cvss / 10.0 * 100)
            elif f.severity_raw.lower() == "critical":
                scores.append(90.0)
            elif f.severity_raw.lower() == "high":
                scores.append(75.0)
            elif f.severity_raw.lower() == "medium":
                scores.append(50.0)
            else:
                scores.append(25.0)

        if not scores:
            return 0.0

        max_score = max(scores)
        # Boost for multiple findings (correlation increases risk)
        boost = min(len(findings) - 1, 3) * 5.0
        combined = min(max_score + boost, 100.0)

        return round(combined, 2)

    def _generate_narrative(
        self,
        findings: list[Any],
        combined_score: float,
    ) -> str:
        """Generate a narrative for the correlated group."""
        titles = [f.title for f in findings[:3]]
        if len(findings) > 3:
            titles.append(f"and {len(findings) - 3} more")

        titles_str = ", ".join(titles)
        risk_class = (
            "critical"
            if combined_score >= 75
            else "high"
            if combined_score >= 50
            else "medium"
            if combined_score >= 25
            else "low"
        )

        return (
            f"Correlated {risk_class} risk ({combined_score:.0f}/100): "
            f"{titles_str} are related findings on the same asset, "
            f"suggesting a broader attack surface."
        )
