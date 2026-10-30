"""VIXOR seed script (T-014).

Creates the admin user from ADMIN_EMAIL / ADMIN_INITIAL_PASSWORD env vars
(argon2-hashed). In development only (SEED_DEMO=true), creates a demo
project with a fixture domain and sample findings.

Never run in production without explicit opt-in.
"""

import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.models.asset
import app.models.audit_log
import app.models.correlation
import app.models.domain
import app.models.finding
import app.models.finding_history
import app.models.finding_score
import app.models.project
import app.models.report
import app.models.scan
import app.models.scan_asset
import app.models.schedule
import app.models.user  # noqa: F401
from app.config import get_settings
from app.models.asset import Asset, ScopeStatus
from app.models.correlation import Correlation
from app.models.domain import Domain, DomainStatus, VerificationMethod
from app.models.finding import Finding, SourceTool
from app.models.finding_history import FindingHistory, HistoryStatus
from app.models.finding_score import FindingScore, RiskClass, ScoredBy
from app.models.project import Project
from app.models.scan import Scan, ScanStatus
from app.models.scan_asset import ScanAsset
from app.models.user import User, UserRole

ph = PasswordHasher()


def seed_admin(db: Session) -> User:
    """Create or reconcile the configured admin account."""
    settings = get_settings()
    email = settings.ADMIN_EMAIL
    password = settings.ADMIN_INITIAL_PASSWORD

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        # Force-reset hash and state to guarantee correct credentials
        existing.password_hash = ph.hash(password)
        existing.is_active = True
        existing.failed_attempts = 0
        existing.locked_until = None
        existing.role = UserRole.admin
        db.add(existing)
        db.flush()
        db.refresh(existing)
        print(
            f"Force-reset admin user {email}: hash, is_active=True, failed_attempts=0, locked_until=None"
        )
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
        created_at=datetime.now(UTC),
    )
    db.add(admin)
    db.flush()
    db.refresh(admin)
    print(f"Created admin user: {email}")
    return admin


def seed_analyst(db: Session) -> User | None:
    """Create an analyst only when explicitly configured for a local demo."""
    email = os.getenv("ANALYST_EMAIL")
    password = os.getenv("ANALYST_INITIAL_PASSWORD")
    if not email or not password:
        return None

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        print(f"Analyst user {email} already exists, skipping.")
        return existing

    password_hash = ph.hash(password)
    analyst = User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=password_hash,
        role=UserRole.analyst,
        is_active=True,
        failed_attempts=0,
        locked_until=None,
        created_at=datetime.now(UTC),
    )
    db.add(analyst)
    db.flush()
    db.refresh(analyst)
    print(f"Created analyst user: {email}")
    return analyst


def seed_demo(db: Session, admin: User) -> None:
    """Create a demo project with fixture domain and sample findings (dev only)."""
    if os.getenv("SEED_DEMO", "false").lower() != "true":
        print("SEED_DEMO not set, skipping demo data.")
        return

    existing_project = (
        db.query(Project)
        .filter(
            Project.owner_id == admin.id,
            Project.name == "Enterprise Security Audit",
        )
        .first()
    )
    if existing_project:
        print("Demo project already exists; skipping to preserve seeded records.")
        return

    project = Project(
        id=str(uuid.uuid4()),
        owner_id=admin.id,
        name="Enterprise Security Audit",
        description="Fixture project for local development",
        created_at=datetime.now(UTC),
    )
    db.add(project)
    db.flush()
    db.refresh(project)

    # Verified domain
    domain = Domain(
        id=str(uuid.uuid4()),
        project_id=project.id,
        root_domain="demo.vixor.local",
        verification_token="demo-token-" + str(uuid.uuid4()),
        verification_method=VerificationMethod.dns_txt,
        status=DomainStatus.verified,
        verified_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db.add(domain)
    db.flush()
    db.refresh(domain)

    # Unverified domain (negative testing)
    domain_unverified = Domain(
        id=str(uuid.uuid4()),
        project_id=project.id,
        root_domain="unverified.vixor.local",
        verification_token="demo-token-" + str(uuid.uuid4()),
        verification_method=VerificationMethod.dns_txt,
        status=DomainStatus.unverified,
        verified_at=None,
        created_at=datetime.now(UTC),
    )
    db.add(domain_unverified)
    db.flush()
    db.refresh(domain_unverified)

    asset = Asset(
        id=str(uuid.uuid4()),
        domain_id=domain.id,
        hostname="app.demo.local",
        ips=["127.0.0.1"],
        is_live=True,
        scope_status=ScopeStatus.in_scope,
        scope_reason=None,
        technologies=["nginx", "Python 3.11", "FastAPI"],
        sensitivity_score=0.7,
        first_seen=datetime.now(UTC) - timedelta(days=7),
        last_seen=datetime.now(UTC),
    )
    db.add(asset)
    db.flush()
    db.refresh(asset)

    unverified_asset = Asset(
        id=str(uuid.uuid4()),
        domain_id=domain_unverified.id,
        hostname="unapp.demo.local",
        ips=["127.0.0.1"],
        is_live=True,
        scope_status=ScopeStatus.in_scope,
        scope_reason=None,
        technologies=["nginx", "Python 3.11"],
        sensitivity_score=0.3,
        first_seen=datetime.now(UTC) - timedelta(days=7),
        last_seen=datetime.now(UTC),
    )
    db.add(unverified_asset)
    db.flush()
    db.refresh(unverified_asset)

    # Scan 1: completed with findings
    scan = Scan(
        id=str(uuid.uuid4()),
        project_id=project.id,
        domain_id=domain.id,
        triggered_by=admin.id,
        status=ScanStatus.completed,
        started_at=datetime.now(UTC) - timedelta(hours=1),
        finished_at=datetime.now(UTC) - timedelta(minutes=50),
        error_summary=None,
    )
    db.add(scan)
    db.flush()
    db.refresh(scan)

    scan_asset = ScanAsset(
        id=str(uuid.uuid4()),
        scan_id=scan.id,
        asset_id=asset.id,
        status="completed",
    )
    db.add(scan_asset)
    db.flush()

    # Finding 1: Nuclei CVE demo
    finding1 = Finding(
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
        evidence={
            "matched_at": "http://app.demo.local/",
            "template": "php-version-detect",
        },
        remediation="Upgrade PHP to a supported version.",
    )
    db.add(finding1)
    db.flush()
    db.refresh(finding1)

    # Finding 2: ZAP XSS
    finding2 = Finding(
        id=str(uuid.uuid4()),
        asset_id=asset.id,
        scan_id=scan.id,
        fingerprint="zap-xss-demo-002",
        source_tool=SourceTool.zap,
        title="Reflected XSS in Search Parameter",
        description="Reflected cross-site search parameter without input sanitization.",
        severity_raw="medium",
        cvss=5.3,
        cve_ids=[],
        evidence={
            "matched_at": "http://app.demo.local/?q=",
            "template": "xss-reflected",
        },
        remediation="Implement input validation and output encoding.",
    )
    db.add(finding2)
    db.flush()
    db.refresh(finding2)

    # Finding 3: Nmap open port
    finding3 = Finding(
        id=str(uuid.uuid4()),
        asset_id=asset.id,
        scan_id=scan.id,
        fingerprint="nmap-open-port-003",
        source_tool=SourceTool.nmap,
        title="Port 8080/SQL-Netware Open",
        description="Port 8080/SQL-Netware is open on the target host.",
        severity_raw="info",
        cvss=2.1,
        cve_ids=[],
        evidence={
            "matched_at": "http://app.demo.local:8080/",
            "template": "version-detect",
        },
        remediation="Close port 8080 if not required, or secure the service.",
    )
    db.add(finding3)
    db.flush()
    db.refresh(finding3)

    # Fixture assets for demo.vixor.local
    asset_demo = Asset(
        id=str(uuid.uuid4()),
        domain_id=domain.id,
        hostname="demo.vixor.local",
        ips=["192.168.1.105"],
        is_live=True,
        scope_status=ScopeStatus.in_scope,
        scope_reason=None,
        technologies=["Nginx 1.24", "PHP 7.4", "MySQL"],
        sensitivity_score=0.7,
        first_seen=datetime.now(UTC) - timedelta(days=7),
        last_seen=datetime.now(UTC),
    )
    db.add(asset_demo)
    db.flush()
    db.refresh(asset_demo)

    asset_api = Asset(
        id=str(uuid.uuid4()),
        domain_id=domain.id,
        hostname="api.vixor.local",
        ips=["192.168.1.106"],
        is_live=True,
        scope_status=ScopeStatus.in_scope,
        scope_reason=None,
        technologies=["FastAPI", "Python 3.11", "Redis"],
        sensitivity_score=0.8,
        first_seen=datetime.now(UTC) - timedelta(days=7),
        last_seen=datetime.now(UTC),
    )
    db.add(asset_api)
    db.flush()
    db.refresh(asset_api)

    # ML Scoring for all findings via xgb model
    score1 = FindingScore(
        finding_id=finding1.id,
        risk_score=72.0,
        risk_class=RiskClass.high,
        model_version="xgb-v1.0.0",
        features={
            "cvss_base": 7.5,
            "in_cisa_kev": 0,
            "epss_score": 0.42,
            "asset_sensitivity": 0.7,
            "internet_exposed": 1.0,
            "auth_required": 0,
            "service_port_risk": 0.5,
            "tool_confidence": 0.9,
            "template_severity": 0.75,
            "age_of_cve_days": 0.0,
            "recurrence_count": 0.0,
            "detected_tech_outdated": 1.0,
        },
        shap_values={
            "cvss_base": 18.5,
            "in_cisa_kev": -2.0,
            "epss_score": 12.3,
            "asset_sensitivity": 5.1,
            "internet_exposed": 8.7,
            "auth_required": -1.2,
            "service_port_risk": 3.3,
            "tool_confidence": 1.1,
            "template_severity": 2.4,
            "age_of_cve_days": 0.0,
            "recurrence_count": 0.0,
            "detected_tech_outdated": 4.2,
        },
        narrative="Risk is high mainly because the CVSS base score is 7.5, the asset is internet-exposed, and the detected technology is outdated.",
        scored_by=ScoredBy.ml,
    )
    db.add(score1)

    score2 = FindingScore(
        finding_id=finding2.id,
        risk_score=48.0,
        risk_class=RiskClass.medium,
        model_version="xgb-v1.0.0",
        features={
            "cvss_base": 5.3,
            "in_cisa_kev": 0,
            "epss_score": 0.35,
            "asset_sensitivity": 0.7,
            "internet_exposed": 1.0,
            "auth_required": 0,
            "service_port_risk": 0.5,
            "tool_confidence": 0.9,
            "template_severity": 0.5,
            "age_of_cve_days": 0.0,
            "recurrence_count": 0.0,
            "detected_tech_outdated": 0.0,
        },
        shap_values={
            "cvss_base": 12.1,
            "in_cisa_kev": -1.5,
            "epss_score": 9.8,
            "asset_sensitivity": 4.2,
            "internet_exposed": 7.1,
            "auth_required": -0.8,
            "service_port_risk": 2.5,
            "tool_confidence": 1.0,
            "template_severity": 1.8,
            "age_of_cve_days": 0.0,
            "recurrence_count": 0.0,
            "detected_tech_outdated": 0.0,
        },
        narrative="Risk is moderate; CVSS 5.3 and internet exposure are contributing factors.",
        scored_by=ScoredBy.ml,
    )
    db.add(score2)

    score3 = FindingScore(
        finding_id=finding3.id,
        risk_score=15.0,
        risk_class=RiskClass.low,
        model_version="xgb-v1.0.0",
        features={
            "cvss_base": 2.1,
            "in_cisa_kev": 0,
            "epss_score": 0.1,
            "asset_sensitivity": 0.3,
            "internet_exposed": 0.0,
            "auth_required": 0,
            "service_port_risk": 0.7,
            "tool_confidence": 0.8,
            "template_severity": 0.1,
            "age_of_cve_days": 0.0,
            "recurrence_count": 0.0,
            "detected_tech_outdated": 0.0,
        },
        shap_values={
            "cvss_base": 3.2,
            "in_cisa_kev": 0.1,
            "epss_score": 0.5,
            "asset_sensitivity": 0.9,
            "internet_exposed": 0.0,
            "auth_required": 0.1,
            "service_port_risk": 1.8,
            "tool_confidence": 0.6,
            "template_severity": 0.2,
            "age_of_cve_days": 0.0,
            "recurrence_count": 0.0,
            "detected_tech_outdated": 0.0,
        },
        narrative="Risk is low; CVSS 2.1 with no internet exposure or KEV listing.",
        scored_by=ScoredBy.ml,
    )
    db.add(score3)

    # Regression tags
    history1 = FindingHistory(
        id=str(uuid.uuid4()),
        fingerprint=finding1.fingerprint,
        asset_id=asset.id,
        scan_id=scan.id,
        status=HistoryStatus.new,
    )
    db.add(history1)

    history2 = FindingHistory(
        id=str(uuid.uuid4()),
        fingerprint=finding2.fingerprint,
        asset_id=asset.id,
        scan_id=scan.id,
        status=HistoryStatus.recurring,
    )
    db.add(history2)

    history3 = FindingHistory(
        id=str(uuid.uuid4()),
        fingerprint=finding3.fingerprint,
        asset_id=asset.id,
        scan_id=scan.id,
        status=HistoryStatus.resolved,
    )
    db.add(history3)

    # Correlation entry (attack chain)
    correlation = Correlation(
        id=str(uuid.uuid4()),
        scan_id=scan.id,
        asset_id=asset.id,
        title="PHP XSS + RCE attack chain",
        narrative="XSS on search parameter combined with outdated PHP version enables remote code execution chain.",
        combined_score=88.0,
        finding_ids=[finding1.id, finding2.id],
    )
    db.add(correlation)

    db.flush()  # Commit all added records (findings, scores, histories, correlation)

    print(
        f"Created demo project '{project.name}' with domains {domain.root_domain} / {domain_unverified.root_domain}"
    )
    print("3 findings with ML scores, SHAP narratives, and regression tags")
    print("1 correlation attack chain entry")


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)

    with Session(bind=engine) as session, session.begin():
        admin = seed_admin(session)
        seed_analyst(session)
        seed_demo(session, admin)
    print("Seeding complete.")


if __name__ == "__main__":
    main()
