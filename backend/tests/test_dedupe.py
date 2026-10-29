"""Unit tests for finding dedupe by fingerprint (T-030).

Tests use an in-memory SQLite database via the db_session fixture. Covers:
- dedupe_findings returns all findings when DB is empty
- dedupe_findings skips findings whose fingerprint already exists
- dedupe_findings scopes by scan_id
- dedupe_findings scopes by asset_id
- findings without a fingerprint are kept (no dedupe key)
- empty input returns empty result
"""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine

from app.models.base import Base
from app.models.finding import Finding
from app.services.scanning.normalizer import dedupe_findings


@pytest.fixture(autouse=True)
def create_tables(db_session):
    """Create all tables and clear findings before each test."""
    from app.config import get_settings

    engine = create_engine(get_settings().DATABASE_URL)
    Base.metadata.create_all(engine)
    db_session.query(Finding).delete()
    db_session.commit()
    engine.dispose()


def _finding(fingerprint: str, source_tool: str = "nmap") -> dict:
    return {
        "fingerprint": fingerprint,
        "source_tool": source_tool,
        "title": f"finding {fingerprint[:8]}",
        "description": "desc",
        "severity_raw": "info",
        "cvss": None,
        "cve_ids": [],
        "evidence": {},
        "remediation": "review",
    }


class TestDedupeFindings:
    """Tests for dedupe_findings."""

    def test_empty_db_keeps_all(self, db_session):
        """With no existing findings, all new findings are returned."""
        findings = [_finding("fp-a"), _finding("fp-b")]
        new, dupes = dedupe_findings(findings, db_session)

        assert len(new) == 2
        assert dupes == []

    def test_skips_existing_fingerprint(self, db_session):
        """Findings whose fingerprint exists in DB are skipped."""
        existing = Finding(
            id=str(uuid4()),
            asset_id=str(uuid4()),
            scan_id=str(uuid4()),
            fingerprint="fp-existing",
            source_tool="nmap",
            title="existing",
            description="existing",
            severity_raw="info",
        )
        db_session.add(existing)
        db_session.commit()

        findings = [
            _finding("fp-existing"),
            _finding("fp-new"),
        ]
        new, dupes = dedupe_findings(findings, db_session)

        assert len(new) == 1
        assert new[0]["fingerprint"] == "fp-new"
        assert dupes == ["fp-existing"]

    def test_scoped_by_scan_id(self, db_session):
        """Dedupe scopes by scan_id: same fingerprint in another scan is kept."""
        scan_a = str(uuid4())
        scan_b = str(uuid4())
        asset_id = str(uuid4())

        existing = Finding(
            id=str(uuid4()),
            asset_id=asset_id,
            scan_id=scan_a,
            fingerprint="fp-shared",
            source_tool="nmap",
            title="existing",
            description="existing",
            severity_raw="info",
        )
        db_session.add(existing)
        db_session.commit()

        findings = [_finding("fp-shared")]

        # Same scan -> skipped
        new, dupes = dedupe_findings(findings, db_session, scan_id=scan_a)
        assert len(new) == 0
        assert dupes == ["fp-shared"]

        # Different scan -> kept
        new, dupes = dedupe_findings(findings, db_session, scan_id=scan_b)
        assert len(new) == 1
        assert dupes == []

    def test_scoped_by_asset_id(self, db_session):
        """Dedupe scopes by asset_id: same fingerprint on another asset is kept."""
        asset_a = str(uuid4())
        asset_b = str(uuid4())
        scan_id = str(uuid4())

        existing = Finding(
            id=str(uuid4()),
            asset_id=asset_a,
            scan_id=scan_id,
            fingerprint="fp-shared",
            source_tool="nmap",
            title="existing",
            description="existing",
            severity_raw="info",
        )
        db_session.add(existing)
        db_session.commit()

        findings = [_finding("fp-shared")]

        new, dupes = dedupe_findings(findings, db_session, asset_id=asset_a)
        assert len(new) == 0
        assert dupes == ["fp-shared"]

        new, dupes = dedupe_findings(findings, db_session, asset_id=asset_b)
        assert len(new) == 1
        assert dupes == []

    def test_keeps_findings_without_fingerprint(self, db_session):
        """Findings with no fingerprint are never deduped away."""
        findings = [
            {"source_tool": "nmap", "title": "no fp", "description": "d"},
            _finding("fp-present"),
        ]
        new, dupes = dedupe_findings(findings, db_session)

        assert len(new) == 2
        assert dupes == []

    def test_empty_input(self, db_session):
        """Empty input returns empty result."""
        new, dupes = dedupe_findings([], db_session)
        assert new == []
        assert dupes == []
