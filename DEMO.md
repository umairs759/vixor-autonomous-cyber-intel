# VIXOR — DEMO Script
## AI-Assisted Continuous Vulnerability Intelligence Platform

### Presentation Script (15-20 minutes)

---

#### 1. Login

```
URL: http://localhost:3000/login
Credentials: admin / TempPass123! (seeded dev account)
```

- Demonstrates JWT-based authentication with httpOnly, Secure, SameSite=Strict cookie
- Role-based access control: admin privileges shown
- Session verified via `/api/v1/auth/me` endpoint

---

#### 2. Domain Verification

```
1. Navigate to "Domains" page → "Register Domain"
2. Enter domain: example.com
3. Choose verification method: DNS TXT or .well-known file
4. Click "Verify"

DNS TXT flow:
- Admin adds TXT record: _vixor-challenge <value> via their DNS provider
- VIXOR validates the TXT record via public DNS lookup
- Status updates to "verified" upon confirmation

File-based flow:
- Admin creates .well-known/vixor-challenge.txt at domain root
- VIXOR fetches http://example.com/.well-known/vixor-challenge.txt
- TXT content matches pre-shared challenge token
```

---

#### 3. Discovery (Asset Enumeration)

```
1. Go to "Projects" → select your project → "Run Discovery"
2. VIXOR chains the discovery pipeline:
   a. Subfinder → enumerates subdomains
   b. crt.sh → fetches CT log certificates
   c. DNS enumeration → A record resolution + wildcard detection
   d. httpx probe → live host verification + technology fingerprinting
3. Scope guard enforces: private IP ranges blocked, CDN/metadata addresses rejected
4. Assets populate the inventory with technology tags
```

*All discovery is scoped to owned domains only. No external network targets are hit in demo mode.*

---

#### 4. Scan Dispatch

```
1. Select a domain → "Launch Scan"
2. Choose scan type:
   - Nmap (safe flags: -sV, safe scripts only, shell=False)
   - OWASP ZAP (safe policy: LOW/MEDIUM, inScopeOnly, non-destructive)
   - Nuclei (excluded tags: dos, intrusive, fuzz, bruteforce)
3. Scan orchestrator chains the tools:
   Nmap → ZAP (optional) → Nuclei
4. Progress tracked via Redis pub/sub → WebSocket endpoint
   GET /api/v1/scans/{id}/ws?token=<JWT>
```

*Demo uses mocked scanner APIs; no actual target is scanned.*

---

#### 5. SHAP Risk Explanation

Once findings are generated, each finding displays:

```
Risk Score: 73/100 (Critical)

Top SHAP Drivers:
├── CVSS Base Score: 7.5 (increases risk)
├── Internet Exposed: yes (increases risk)
├── CISA KEV: yes (increases risk)
├── Service Port Risk: high-risk port (increases risk)
└── Template Severity: critical (increases risk)
```

**Narrative Generation** (deterministic, no LLM):

> "Risk is 73/100 mainly because CVSS base score of 7.5 increases risk, this CVE is listed in CISA KEV (exploitation likelihood is high), public exploit is available (exploitation increases risk), and the asset is internet-exposed (exploitation increases risk)."

- SHAP TreeExplainer produces deterministic feature contributions
- Top-5 drivers always explained
- Narrative templates mapped to each feature
- Zero LLM usage for scoring or narratives

---

#### 6. Regression Status

```
Finding reappeared after fix → status: RECURRING
Finding carried over from previous scan → status: NEW
Finding from previous scan, still present → status: RECURRING
Finding resolved in latest scan → status: RESOLVED
```

- Classification: NEW | RECURRING | REINTRODUCED | RESOLVED
- Based on fingerprint dedupe across scan cycles
- Previous scan ID tracked per asset

---

#### 7. Correlation Engine

Groupings by rule-based clustering:

```
Finding A (XSS on /login) + Finding B (XSS on /login old) → 
Cluster: "XSS on login form" 
Combined Score: max individual scores, adjusted by scope
Narrative: "Two XSS vulnerabilities detected on login endpoint; both allow script injection via parameter t."
```

- Rule-based grouping by template-id + hostname + path proximity
- Combined score weights scanner confidence + severity + recurrence
- Narrative generated from deterministic templates

---

#### 8. PDF Report Export

```
1. Navigate to "Reports" page
2. Click "Generate Report" for a scan range
3. PDF generated with:
   - Executive summary (scan scope, total findings, risk distribution)
   - Severity distribution chart (High/Critical counts)
   - Findings table (title, severity, SHAP drivers, remediation)
   - Regression analysis (NEW/RECURRING/RESOLVED per finding)
   - Correlation group summary
   - Remediation prioritization matrix
4. Download PDF for stakeholder review
```

Generated using ReportLab with professional formatting, charts, and executive summary.

---

#### 9. Admin Functions

```
1. User management: create/reset/delete users, assign roles (admin/analyst/viewer)
2. Audit log review: search/filter audit entries, export evidence
3. Scan scheduling: Celery Beat re-verifies domain ownership before each run
4. System health: /health endpoint, Redis connectivity, DB status
```

---

### Demo Script Summary (8-minute version)

1. **Login** (30 sec) - auth + RBAC
2. **Register + Verify Domain** (45 sec) - DNS TXT + file challenges
3. **Run Discovery** (1 min) - subfinder → ct.log → dns → httpx, scope-guard enforced
4. **Launch Scan** (45 sec) - ZAP/Nuclei mocked, progress over WebSocket
5. **View Findings + SHAP Narrative** (1 min) - risk gauge, top drivers, auto narrative
6. **Regression + Correlation Views** (30 sec) - statuses, grouped findings
7. **PDF Report Export** (45 sec) - download, executive summary
8. **Admin Quick Look** (30 sec) - users, audit logs

**Total**: ~15 minutes

---

### Key Technical Guarantees (for technical audience)

- All scanner commands: `subprocess.run(args, shell=False)` — no shell interpolation
- Scope guard: enforced before each asset scan (DNS TXT + IP resolution blocks)
- ML scoring: XGBoost model `ml/artifacts/xgb-v1.0.0` + SHAP TreeExplainer
- Zero LLM usage for risk scoring or narrative generation
- Regression: NEW | RECURRING | REINTRODUCED | RESOLVED (fingerprint dedupe)
- Correlation: rule-based grouping + combined score + deterministic narrative
- PDF: ReportLab exec summary, charts, findings, remediation, regression
- DNS TXT barrier: domain ownership verified before scan dispatch
- Celery Beat: re-verifies ownership before scheduled scan re-runs
- 209/209 backend pytest tests passing, ruff/mypy 0 errors