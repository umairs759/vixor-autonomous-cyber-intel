#!/usr/bin/env python
"""VIXOR System Health Check Script."""
import os
import sys

os.chdir(r"C:\Users\usamah\Desktop\VIXOR — Autonomous\backend")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.core.security import verify_password
from app.models.correlation import Correlation
from app.models.domain import Domain
from app.models.finding import Finding
from app.models.finding_score import FindingScore
from app.models.project import Project
from app.models.user import User, UserRole

# Use the same DATABASE_URL as the application
engine = create_engine(str(get_settings().DATABASE_URL))
Session = sessionmaker(bind=engine)
db = Session()

errors = []
warnings = []

# 1. Admin user check
admin = db.query(User).filter(User.email == "admin@example.com").first()
if not admin:
    errors.append("FAIL: Admin user not in DB")
else:
    pw_ok = verify_password("Admin123!", admin.password_hash)
    if not pw_ok:
        errors.append("FAIL: Admin password hash does NOT match Admin123!")
    else:
        print("PASS: Admin user exists, password matches Admin123!")
    if admin.is_active != True:
        errors.append("FAIL: admin.is_active is not True")
    else:
        print("PASS: admin.is_active = True")
    if admin.failed_attempts != 0:
        errors.append("FAIL: admin.failed_attempts is not 0")
    else:
        print("PASS: admin.failed_attempts = 0")
    if admin.role != UserRole.admin:
        errors.append("FAIL: admin.role is not 'admin'")
    else:
        print("PASS: admin.role = 'admin'")

# 2. Analyst user check
analyst = db.query(User).filter(User.email == "analyst@example.com").first()
if not analyst:
    warnings.append("WARN: Analyst user not found in DB")
else:
    if analyst.is_active != True:
        errors.append("FAIL: analyst.is_active is not True")
    else:
        print("PASS: Analyst user exists and is_active=True")

# 3. Project check
projects = db.query(Project).all()
print(f"\nProjects ({len(projects)}):")
for p in projects:
    print(f"  - {p.name} (scans={len(p.scans) if p.scans else 0})")
    if "Enterprise Security Audit" in p.name:
        print("  PASS: Demo project found")

# 4. Domain check
domains = db.query(Domain).all()
print(f"\nDomains ({len(domains)}):")
for d in domains:
    verified = "VERIFIED" if d.status.name == "verified" else "UNVERIFIED"
    print(f"  - {d.root_domain}: {verified}")
    if "demo.vixor.local" in d.root_domain and d.status.name != "verified":
        errors.append("FAIL: demo.vixor.local should be verified")

# 5. Findings check
findings = db.query(Finding).all()
print(f"\nFindings ({len(findings)}):")
for f in findings:
    score = db.query(FindingScore).filter(FindingScore.finding_id == f.id).first()
    has_score = score is not None and score.risk_score is not None
    has_narrative = score is not None and score.narrative is not None and len(score.narrative) > 0
    print(f"  - {f.title}: risk_score={score.risk_score if score else 'N/A'}, narrative={'YES' if has_narrative else 'NO'}, shap_present={bool(score.shap_values) if score else False}")
    if not has_score:
        errors.append(f"FAIL: Finding {f.id} missing ml_risk_score")
    if not has_narrative:
        errors.append(f"FAIL: Finding {f.id} missing risk_narrative")

# 6. Correlation check
correlations = db.query(Correlation).all()
print(f"\nCorrelations ({len(correlations)}):")
for c in correlations:
    has_score = c.combined_score is not None and c.combined_score == 88
    has_findings = len(c.finding_ids) > 0
    print(f"  - {c.title}: combined_score={c.combined_score}, finding_links={len(c.finding_ids)}")
    if not has_score:
        errors.append("FAIL: Correlation combined_risk_score is not 88")
    if not has_findings:
        errors.append("FAIL: Correlation has no linked findings")

db.close()

print("\n" + "="*50)
result_code = 0 if not errors else 1
if errors:
    print(f"RESULT: {len(errors)} FAILURE(S), {len(warnings)} WARNING(S)")
    for e in errors:
        print(f"  ERROR: {e}")
    for w in warnings:
        print(f"  WARN: {w}")
else:
    print("RESULT: ALL CHECKS PASSED")
sys.exit(result_code)