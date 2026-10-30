"""Isolated seed idempotency and admin credential checks."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import verify_password
from app.models.base import Base
from app.models.correlation import Correlation
from app.models.domain import Domain, DomainStatus
from app.models.finding import Finding
from app.models.finding_history import FindingHistory
from app.models.finding_score import FindingScore
from app.models.project import Project
from app.models.user import User
from scripts.seed import seed_admin, seed_demo


def test_demo_seed_is_idempotent_and_admin_is_configured(monkeypatch):
    monkeypatch.setenv("SEED_DEMO", "true")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    settings = get_settings()

    with Session(engine) as db, db.begin():
        admin = seed_admin(db)
        seed_demo(db, admin)
    with Session(engine) as db, db.begin():
        admin = seed_admin(db)
        seed_demo(db, admin)

    with Session(engine) as db:
        admin = db.query(User).filter(User.email == settings.ADMIN_EMAIL).one()
        assert admin.is_active is True
        assert admin.failed_attempts == 0
        assert verify_password(settings.ADMIN_INITIAL_PASSWORD, admin.password_hash)
        assert (
            db.query(Project).filter_by(name="Enterprise Security Audit").count() == 1
        )
        domains = db.query(Domain).all()
        assert len(domains) == 2
        assert {(domain.root_domain, domain.status) for domain in domains} == {
            ("demo.vixor.local", DomainStatus.verified),
            ("unverified.vixor.local", DomainStatus.unverified),
        }
        assert db.query(Finding).count() == 3
        scores = db.query(FindingScore).all()
        assert len(scores) == 3
        assert all(score.risk_score is not None for score in scores)
        assert all(score.shap_values and score.narrative for score in scores)
        assert db.query(FindingHistory).count() == 3
        correlation = db.query(Correlation).one()
        assert correlation.combined_score == 88
        assert len(correlation.finding_ids) >= 2

    engine.dispose()
