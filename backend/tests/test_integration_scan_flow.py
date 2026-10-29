"""Integration tests for scan flow with mocked scanners (T-053)."""

from unittest.mock import patch

from app.models.asset import Asset
from app.models.domain import Domain, DomainStatus, VerificationMethod
from app.models.project import Project
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.workers.tasks_scan import run_scan


def test_scan_flow_mocked(db_session):
    user = User(email=f"u-{__import__('uuid').uuid4()}@example.com", password_hash="x", role="admin")
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
        verified_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    db_session.add(domain)
    db_session.commit()
    db_session.refresh(domain)

    asset = Asset(domain_id=domain.id, hostname="host.example.com")
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    scan = Scan(project_id=project.id, domain_id=domain.id, triggered_by=user.id, status=ScanStatus.queued)
    db_session.add(scan)
    db_session.commit()
    db_session.refresh(scan)

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
            }
        ]
    }

    with patch("app.workers.tasks_scan.ScanOrchestrator") as mock_orch:
        mock_orch.return_value.scan_asset.return_value = mocked_result
        result = run_scan(str(scan.id), str(domain.id), [str(asset.id)])

    assert result["status"] == "completed"
    assert result["findings"]
