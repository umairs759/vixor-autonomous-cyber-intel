"""Unit tests for regression engine (T-037, T-052)."""

import uuid

from app.models.asset import Asset
from app.models.domain import Domain, DomainStatus, VerificationMethod
from app.models.finding import Finding
from app.models.project import Project
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.services.regression_engine import RegressionEngine


def _setup(db, suffix="1"):
    _user = User(email=f"u{suffix}-{uuid.uuid4()}@example.com", password_hash="x", role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    project = Project(name=f"p-{suffix}", owner_id=user.id)
    db.add(project)
    db.commit()
    db.refresh(project)

    domain = Domain(
        project_id=project.id,
        root_domain=f"example{suffix}.com",
        verification_token="tok",
        verification_method=VerificationMethod.dns_txt,
        status=DomainStatus.verified,
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)

    asset = Asset(domain_id=domain.id, hostname=f"host.example{suffix}.com")
    db.add(asset)
    db.commit()
    db.refresh(asset)

    scan1 = Scan(project_id=project.id, domain_id=domain.id, triggered_by=user.id, status=ScanStatus.completed)
    db.add(scan1)
    db.commit()
    db.refresh(scan1)

    return project, domain, asset, scan1


def test_regression_new(db_session):
    project, domain, asset, scan1 = _setup(db_session, "a")
    finding = Finding(
        asset_id=asset.id, scan_id=scan1.id, fingerprint="fp1", title="t", description="d", severity_raw="low", source_tool="nmap"
    )
    db_session.add(finding)
    db_session.commit()

    engine = RegressionEngine(db_session)
    results = engine.classify_scan_findings(str(scan1.id))
    assert results[0]["status"] == "new"


def test_regression_recurring_and_resolved(db_session):
    project, domain, asset, scan1 = _setup(db_session, "b")
    f1 = Finding(asset_id=asset.id, scan_id=scan1.id, fingerprint="fp1", title="t", description="d", severity_raw="low", source_tool="nmap")
    db_session.add(f1)
    db_session.commit()

    engine = RegressionEngine(db_session)
    engine.classify_scan_findings(str(scan1.id))

    scan2 = Scan(project_id=project.id, domain_id=domain.id, triggered_by=project.owner_id, status=ScanStatus.completed)
    db_session.add(scan2)
    db_session.commit()
    db_session.refresh(scan2)

    f2 = Finding(asset_id=asset.id, scan_id=scan2.id, fingerprint="fp1", title="t", description="d", severity_raw="low", source_tool="nmap")
    db_session.add(f2)
    db_session.commit()

    results = engine.classify_scan_findings(str(scan2.id), previous_scan_id=str(scan1.id))
    statuses = {r["fingerprint"]: r["status"] for r in results}
    assert statuses["fp1"] == "recurring"

    # scan3 with no findings resolves fp1
    scan3 = Scan(project_id=project.id, domain_id=domain.id, triggered_by=project.owner_id, status=ScanStatus.completed)
    db_session.add(scan3)
    db_session.commit()
    db_session.refresh(scan3)

    results3 = engine.classify_scan_findings(str(scan3.id), previous_scan_id=str(scan2.id))
    statuses3 = {r["fingerprint"]: r["status"] for r in results3}
    assert statuses3.get("fp1") == "resolved"
