"""Unit tests for correlation engine (T-038, T-052)."""

from app.models.asset import Asset
from app.models.domain import Domain, DomainStatus, VerificationMethod
from app.models.finding import Finding
from app.models.project import Project
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.services.correlation_engine import CorrelationEngine


def test_correlation_groups(db_session):
    import uuid

    user = User(email=f"u-{uuid.uuid4()}@example.com", password_hash="x", role="admin")
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
    )
    db_session.add(domain)
    db_session.commit()
    db_session.refresh(domain)

    asset = Asset(domain_id=domain.id, hostname="host.example.com")
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    scan = Scan(project_id=project.id, domain_id=domain.id, triggered_by=user.id, status=ScanStatus.completed)
    db_session.add(scan)
    db_session.commit()
    db_session.refresh(scan)

    for i in range(2):
        f = Finding(
            asset_id=asset.id,
            scan_id=scan.id,
            fingerprint=f"fp{i}",
            title=f"XSS issue {i}",
            description="missing header",
            severity_raw="high",
            source_tool="zap",
            evidence={"port": 80},
        )
        db_session.add(f)
    db_session.commit()

    engine = CorrelationEngine(db_session)
    groups = engine.correlate_findings(str(scan.id), str(asset.id))
    assert len(groups) >= 1
    assert groups[0]["combined_score"] > 0
