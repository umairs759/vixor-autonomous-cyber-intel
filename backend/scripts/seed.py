"""VIXOR seed script (T-014).

Creates the admin user from ADMIN_EMAIL / ADMIN_INITIAL_PASSWORD env vars
(argon2-hashed). In development only (SEED_DEMO=true), creates a demo
project with a fixture domain and sample findings.

Never run in production without explicit opt-in.
"""

import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

from argon2 import PasswordHasher
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings  # noqa: E402
from app.models.base import Base  # noqa: E402
import app.models.user  # noqa: F401
import app.models.audit_log  # noqa: F401
import app.models.project  # noqa: F401
import app.models.domain  # noqa: F401
import app.models.asset  # noqa: F401
import app.models.scan  # noqa: F401
import app.models.scan_asset  # noqa: F401
import app.models.finding  # noqa: F401
import app.models.finding_score  # noqa: F401
import app.models.finding_history  # noqa: F401
import app.models.correlation  # noqa: F401
import app.models.report  # noqa: F401
import app.models.schedule  # noqa: F401
from app.models.user import User, UserRole  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.domain import Domain, DomainStatus, VerificationMethod  # noqa: E402
from app.models.asset import Asset, ScopeStatus  # noqa: E402
from app.models.scan import Scan, ScanStatus  # noqa: E402
from app.models.scan_asset import ScanAsset  # noqa: E402
from app.models.finding import Finding, SourceTool  # noqa: E402
from app.models.finding_score import FindingScore, RiskClass, ScoredBy  # noqa: E402
from app.models.audit_log import AuditLog  # noqa: E402

ph = PasswordHasher()


def seed_admin(db: Session) -> User:
    """Create the admin user from env vars."""
    settings = get_settings()
    email = settings.ADMIN_EMAIL
    password = settings.ADMIN_INITIAL_PASSWORD

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        print(f"Admin user {email} already exists, skipping.")
        return existing

    password_hash = ph.hash(password)
    admin = User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=password_hash,
        role=UserRole.admin,
        is_active=True,
        failed_attempts=0,
        locked_until=None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    print(f"Created admin user: {email}")
    return admin


def seed_demo(db: Session, admin: User) -> None:
    """Create a demo project with fixture domain and sample findings (dev only)."""
    if os.getenv("SEED_DEMO", "false").lower() != "true":
        print("SEED_DEMO not set, skipping demo data.")
        return

    project = Project(
        id=str(uuid.uuid4()),
        owner_id=admin.id,
        name="Demo Project",
        description="Fixture project for local development",
        created_at=datetime.now(timezone.utc),
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    domain = Domain(
        id=str(uuid.uuid4()),
        project_id=project.id,
        root_domain="example.local",
        verification_token="demo-token-" + str(uuid.uuid4()),
        verification_method=VerificationMethod.dns_txt,
        status=DomainStatus.verified,
        verified_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)

    asset = Asset(
        id=str(uuid.uuid4()),
        domain_id=domain.id,
        hostname="app.example.local",
        ips=["93.184.216.34"],
        is_live=True,
        scope_status=ScopeStatus.in_scope,
        scope_reason=None,
        technologies=["nginx", "PHP 7.4"],
        sensitivity_score=0.7,
        first_seen=datetime.now(timezone.utc) - timedelta(days=7),
        last_seen=datetime.now(timezone.utc),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    scan = Scan(
        id=str(uuid.uuid4()),
        project_id=project.id,
        domain_id=domain.id,
        triggered_by=admin.id,
        status=ScanStatus.completed,
        started_at=datetime.now(timezone.utc) - timedelta(hours=1),
        finished_at=datetime.now(timezone.utc) - timedelta(minutes=50),
        error_summary=None,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    scan_asset = ScanAsset(
        id=str(uuid.uuid4()),
        scan_id=scan.id,
        asset_id=asset.id,
        status="completed",
    )
    db.add(scan_asset)
    db.commit()

    finding = Finding(
        id=str(uuid.uuid4()),
        asset_id=asset.id,
        scan_id=scan.id,
        fingerprint="nuclei-cve-2024-demo-001",
        source_tool=SourceTool.nuclei,
        title="Outdated PHP Version",
        description="The server is running PHP 7.4 which is end-of-life and has known vulnerabilities.",
        severity_raw="high",
        cvss=7.5,
        cve_ids=["CVE-2024-1234"],
        evidence={"matched_at": "http://app.example.local/", "template": "php-version-detect"},
        remediation="Upgrade PHP to a supported version.",
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)

    score = FindingScore(
        finding_id=finding.id,
        risk_score=72.0,
        risk_class=RiskClass.high,
        model_version="rf-v1.0.0",
        features={"cvss_base": 7.5, "in_cisa_kev": 0, "epss_score": 0.42},
        shap_values={"cvss_base": 18.5, "in_cisa_kev": -2.0, "epss_score": 12.3},
        narrative="Risk is high mainly because the CVSS base score is 7.5 and the service is internet-exposed.",
        scored_by=ScoredBy.fallback,
    )
    db.add(score)

    history = FindingHistory(
        id=str(uuid.uuid4()),
        fingerprint=finding.fingerprint,
        asset_id=asset.id,
        scan_id=scan.id,
        status=__import__("app.models.finding_history", fromlist=["HistoryStatus"]).HistoryStatus.new,
    )
    db.add(history)
    db.commit()

    print(f"Created demo project '{project.name}' with domain {domain.root_domain}")


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)

    # Ensure tables exist (create_all is idempotent)
    Base.metadata.create_all(engine)

    session = Session(bind=engine)
    try:
        admin = seed_admin(session)
        seed_demo(session, admin)
        print("Seeding complete.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
