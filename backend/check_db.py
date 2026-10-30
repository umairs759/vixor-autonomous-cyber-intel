import os

os.chdir(r'C:\Users\usamah\Desktop\VIXOR — Autonomous\backend')
os.environ['SEED_DEMO'] = 'true'

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models.correlation import Correlation
from app.models.domain import Domain
from app.models.finding import Finding
from app.models.finding_score import FindingScore
from app.models.project import Project
from app.models.user import User

engine = create_engine(str(get_settings().DATABASE_URL))
Session = sessionmaker(bind=engine)
db = Session()

# Check users
admins = db.query(User).filter(User.email == 'admin@example.com').all()
print(f'Admin count: {len(admins)}')
for a in admins:
    print(f'  email={a.email}, is_active={a.is_active}, failed_attempts={a.failed_attempts}, role={a.role}')

analysts = db.query(User).filter(User.email == 'analyst@example.com').all()
print(f'Analyst count: {len(analysts)}')
for a in analysts:
    print(f'  email={a.email}, is_active={a.is_active}, failed_attempts={a.failed_attempts}, role={a.role}')

# Check projects
projects = db.query(Project).all()
print(f'Project count: {len(projects)}')
for p in projects:
    print(f'  {p.name}, scans={len(p.scans) if p.scans else 0}')

# Check domains
domains = db.query(Domain).all()
print(f'Domain count: {len(domains)}')
for d in domains:
    ver = 'VERIFIED' if d.status.name == 'verified' else 'UNVERIFIED'
    print(f'  {d.root_domain}: {ver}')

# Check findings
findings = db.query(Finding).all()
print(f'Finding count: {len(findings)}')
for f in findings:
    score = db.query(FindingScore).filter(FindingScore.finding_id == f.id).first()
    has_score = score is not None and score.risk_score is not None
    has_narrative = score is not None and score.narrative is not None and len(score.narrative) > 0
    risk = score.risk_score if score else 'N/A'
    nar = 'YES' if has_narrative else 'NO'
    shap = bool(score.shap_values) if score else False
    print(f'  {f.id[:8]}: {f.title}, severity={f.severity_raw}, risk_score={risk}, narrative={nar}, shap={shap}')

# Check correlations
correlations = db.query(Correlation).all()
print(f'Correlation count: {len(correlations)}')
for c in correlations:
    has_score = c.combined_score is not None and c.combined_score == 88
    has_findings = len(c.finding_ids) > 0
    print(f'  {c.id[:8]}: title={c.title}, combined_score={c.combined_score}, finding_links={len(c.finding_ids)}, has_score88={has_score}')

db.close()