"""Integration tests for scan flow with mocked scanners (T-053)."""

from unittest.mock import patch

from app.models.asset import Asset, ScopeStatus
from app.models.correlation import Correlation
from app.models.domain import Domain, DomainStatus, VerificationMethod
from app.models.finding import Finding
from app.models.finding_history import FindingHistory
from app.models.finding_score import FindingScore
from app.models.project import Project
from app.models.scan import Scan, ScanStatus
from app.models.scan_asset import ScanAsset
from app.models.user import User
from app.workers.tasks_scan import run_scan


def test_scan_flow_mocked(db_session):
    user = User(
        email=f"u-{__import__('uuid').uuid4()}@example.com",
        password_hash="x",
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    project = Project(name="p", owner_id=user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    domain = Domain(
        project_id=project.id,
        root_domain="example.com",
        verification_token="tok",
        verification_method=VerificationMethod.dns_txt,
        status=DomainStatus.verified,
        verified_at=__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ),
    )
    db_session.add(domain)
    db_session.commit()
    db_session.refresh(domain)

    asset = Asset(
        domain_id=domain.id,
        hostname="host.example.com",
        scope_status=ScopeStatus.in_scope,
        is_live=True,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    scan = Scan(
        project_id=project.id,
        domain_id=domain.id,
        triggered_by=user.id,
        status=ScanStatus.queued,
    )
    db_session.add(scan)
    db_session.commit()
    db_session.refresh(scan)
    db_session.add(ScanAsset(scan_id=scan.id, asset_id=asset.id, status="pending"))
    db_session.commit()

    mocked_result = {
        "findings": [
            {
                "fingerprint": "fp1",
                "source_tool": "nuclei",
                "title": "Test finding",
                "description": "desc",
                "severity_raw": "high",
                "cvss": 7.5,
                "cve_ids": [],
                "evidence": {"port": 80},
                "remediation": "fix",
            },
            {
                "fingerprint": "fp2",
                "source_tool": "zap",
                "title": "Missing Security Header",
                "description": "A security response header is missing.",
                "severity_raw": "medium",
                "cvss": 5.0,
                "cve_ids": [],
                "evidence": {"port": 80},
                "remediation": "Set the required response header.",
            },
        ]
    }

    with (
        patch("app.workers.tasks_scan.is_in_scope", return_value=(True, None)),
        patch("app.workers.tasks_scan._publish_progress"),
        patch("app.workers.tasks_scan.ScanOrchestrator") as mock_orch,
    ):
        mock_orch.return_value.scan_asset.return_value = mocked_result
        result = run_scan(str(scan.id), str(domain.id), [str(asset.id)])

    assert result["status"] == "completed"
    assert result["findings"]
    db_session.expire_all()
    assert db_session.query(Finding).filter_by(scan_id=scan.id).count() == 2
    assert db_session.query(FindingScore).count() == 2
    assert db_session.query(FindingHistory).filter_by(scan_id=scan.id).count() == 2
    assert db_session.query(Correlation).filter_by(scan_id=scan.id).count() == 1
