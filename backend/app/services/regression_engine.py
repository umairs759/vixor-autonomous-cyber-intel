"""VIXOR — Regression engine (T-037).

Classifies findings per scan cycle as NEW, RECURRING, REINTRODUCED, or RESOLVED.
"""

from typing import Any

from app.core.logging import get_logger
from app.models.asset import Asset
from app.models.finding import Finding
from app.models.finding_history import FindingHistory, HistoryStatus

logger = get_logger("ml.regression")


class RegressionEngine:
    """Classifies findings across scan cycles."""

    def __init__(self, db_session: Any) -> None:
        self.db = db_session

    def classify_finding(
        self,
        fingerprint: str,
        asset: Asset,
        scan_id: str,
        previous_scan_id: str | None = None,
    ) -> HistoryStatus:
        """Classify a finding's regression status.

        Logic:
        - NEW: fingerprint not seen in any previous scan for this asset
        - RECURRING: fingerprint seen in the immediately previous scan
        - REINTRODUCED: fingerprint seen in an earlier scan but not the previous one
        - RESOLVED: fingerprint was in previous scan but not in current (called separately)
        """
        # Check if fingerprint exists in any previous scan for this asset
        prev_history = (
            self.db.query(FindingHistory)
            .filter(
                FindingHistory.fingerprint == fingerprint,
                FindingHistory.asset_id == asset.id,
            )
            .order_by(FindingHistory.created_at.desc())
            .first()
        )

        if prev_history is None:
            # First time seeing this fingerprint
            status = HistoryStatus.new
        else:
            # Check if it was in the immediately previous scan
            if previous_scan_id and prev_history.scan_id == previous_scan_id:
                status = HistoryStatus.recurring
            else:
                # Seen before but not in the immediately previous scan
                status = HistoryStatus.reintroduced

        # Record the history entry
        history_entry = FindingHistory(
            fingerprint=fingerprint,
            asset_id=asset.id,
            scan_id=scan_id,
            status=status,
        )
        self.db.add(history_entry)
        self.db.commit()

        logger.debug(
            "fingerprint classified",
            fingerprint=fingerprint,
            asset_id=asset.id,
            scan_id=scan_id,
            status=status.value,
        )

        return status

    def classify_scan_findings(
        self,
        scan_id: str,
        previous_scan_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Classify all findings in a scan cycle.

        Returns list of classification results.
        """
        from app.models.asset import Asset

        findings = self.db.query(Finding).filter(Finding.scan_id == scan_id).all()

        results: list[dict[str, Any]] = []
        for finding in findings:
            asset = self.db.query(Asset).filter(Asset.id == finding.asset_id).first()
            if not asset:
                continue

            status = self.classify_finding(
                fingerprint=finding.fingerprint,
                asset=asset,
                scan_id=scan_id,
                previous_scan_id=previous_scan_id,
            )

            results.append(
                {
                    "finding_id": finding.id,
                    "fingerprint": finding.fingerprint,
                    "asset_id": finding.asset_id,
                    "hostname": asset.hostname,
                    "status": status.value,
                }
            )

        return results
