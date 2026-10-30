from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.asset import Asset, ScopeStatus
from app.models.base import Base
from app.models.domain import Domain, DomainStatus, VerificationMethod
from app.models.project import Project
from app.models.scan import ScanStatus
from app.models.user import User, UserRole
from app.services import scan_admission
from app.services.scan_admission import ScanConcurrencyLimit, create_queued_scan


def setup_db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine


def make_project(db, email):
    user = User(email=email, password_hash="test", role=UserRole.analyst)
    db.add(user); db.flush()
    project = Project(owner_id=user.id, name=email)
    db.add(project); db.flush()
    domain = Domain(project_id=project.id, root_domain="example.test", verification_token="x", verification_method=VerificationMethod.file, status=DomainStatus.verified)
    db.add(domain); db.flush()
    asset = Asset(domain_id=domain.id, hostname="host.example.test", scope_status=ScopeStatus.in_scope)
    db.add(asset); db.flush()
    return user, project, domain, asset


def test_project_limit_reserves_slot_and_releases_on_terminal_status(monkeypatch):
    monkeypatch.setattr(scan_admission, "get_settings", lambda: SimpleNamespace(MAX_CONCURRENT_SCANS_PER_PROJECT=1))
    engine=setup_db()
    with Session(engine) as db:
        user, project, domain, asset=make_project(db,"one@example.test")
        first=create_queued_scan(db,project_id=project.id,domain_id=domain.id,triggered_by=user.id,assets=[asset]); db.commit()
        with pytest.raises(ScanConcurrencyLimit):
            create_queued_scan(db,project_id=project.id,domain_id=domain.id,triggered_by=user.id,assets=[asset])
        db.rollback()
        first.status=ScanStatus.failed; db.commit()
        second=create_queued_scan(db,project_id=project.id,domain_id=domain.id,triggered_by=user.id,assets=[asset]); db.commit()
        assert first.id != second.id
    engine.dispose()


def test_scan_limits_are_independent_per_project(monkeypatch):
    monkeypatch.setattr(scan_admission, "get_settings", lambda: SimpleNamespace(MAX_CONCURRENT_SCANS_PER_PROJECT=1))
    engine=setup_db()
    with Session(engine) as db:
        user1,p1,d1,a1=make_project(db,"a@example.test")
        user2,p2,d2,a2=make_project(db,"b@example.test")
        create_queued_scan(db,project_id=p1.id,domain_id=d1.id,triggered_by=user1.id,assets=[a1])
        other=create_queued_scan(db,project_id=p2.id,domain_id=d2.id,triggered_by=user2.id,assets=[a2])
        assert other.project_id == p2.id
    engine.dispose()
