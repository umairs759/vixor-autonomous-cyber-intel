# VIXOR — Autonomous Prompt Pack

## ASSUMPTIONS (stated up front)

1. Project: VIXOR, AI-assisted continuous vulnerability intelligence platform (COMSATS FYP). Scope strictly follows the scope document: Authentication & RBAC, Attack Surface Discovery, Vulnerability Scanning, AI/XAI Engine, Dashboard & Reporting, plus Correlation (BO-5) and Regression Intelligence (BO-6).
2. Users: Administrator and Analyst roles. Management stakeholders get a read-only executive summary view and PDF reports.
3. Backend: FastAPI (Python 3.11), SQLAlchemy 2.0 + Alembic, PostgreSQL 15, Redis 7, Celery 5 + Celery Beat.
4. Frontend: React 18 via **Next.js 14 App Router** (mandated for React projects), TypeScript, Tailwind CSS, Recharts, Zod for form and API-response validation. Route protection through Next.js middleware.
5. Scanners (each in isolated containers): Subfinder, httpx (live host + fingerprinting), Nmap, OWASP ZAP (daemon mode, API), Nuclei.
6. ML: scikit-learn RandomForest + XGBoost, SHAP TreeExplainer. **LLMs are never used for scoring.** Natural-language risk narratives are template-based, generated deterministically from SHAP values.
7. Training data: NVD/CVE feed, EPSS scores, CISA KEV catalog, Nuclei template metadata. A synthetic-label strategy is documented in ARCHITECTURE.md because no labeled ground truth exists.
8. Deployment: Docker Compose (api, worker, beat, web, postgres, redis, zap, scanner-tools).
9. Design direction: premium dark luxury, mobile-first responsive (security-ops aesthetic: near-black background, electric cyan + amber accents).
10. Ethics: only authorized, ownership-verified domains are scanned (LI-1, BO-10). No exploit execution or destructive testing (LI-2). Nuclei runs with non-intrusive templates only (exclude tags: dos, intrusive, fuzz, bruteforce).

---

## PART 0: AUTOPILOT MASTER PROMPT (Paste to OpenCode First)

```
You are an autonomous senior full-stack and security engineer building "VIXOR", an AI-assisted continuous vulnerability intelligence platform.

BEFORE ANY ACTION, read in full: RULES.md, PRD.md, ARCHITECTURE.md, DESIGN.md, MEMORY.md, and every file inside /security.

EXECUTION PROTOCOL
1. Follow RULES.md strictly. It overrides your defaults.
2. Execute TASKS.md sequentially from top to bottom. Work on exactly ONE atomic task at a time. Never skip ahead.
3. After each task: (a) run the relevant tests, linter, and type checks; (b) fix failures before moving on; (c) tick the task in TASKS.md ([x]); (d) append decisions, known issues, and new env vars to MEMORY.md; (e) make one conventional commit.
4. Never modify files unrelated to the current task.
5. Non-negotiable product constraints:
   - A scan may only target a domain whose ownership is verified AND an asset that passes scope validation. Enforce this in the service layer AND in the Celery task itself (defense in depth).
   - No exploit execution or destructive testing, ever.
   - Risk scoring uses trained RandomForest/XGBoost models only. SHAP provides explanations. Never call an LLM for scoring.
   - Every state-changing action writes an audit log row.
6. If something is ambiguous, choose the safest engineering option, document it in MEMORY.md under "Decisions", and continue autonomously without waiting for input.
7. If a task is blocked by an external dependency (e.g., dataset download fails), implement a clearly flagged fallback (fixture data), log it as technical debt in MEMORY.md, and continue.
8. Stop only when every task in TASKS.md is ticked and the final security checklist in /security/security-checklist.md is fully verified. Then print a completion report.
```

---

## PART 1: PROJECT SCAFFOLDING PROMPT

```
Create the following directory structure and write each file with EXACTLY the content given below. Do not write any application code in this step. Commit as "chore: scaffold project documentation".

vixor/
├── PRD.md
├── ARCHITECTURE.md
├── RULES.md
├── DESIGN.md
├── TASKS.md
├── MEMORY.md
├── security/
│   ├── threat-model.md
│   ├── attack-surface.md
│   ├── secrets.md
│   └── security-checklist.md
├── backend/
├── frontend/
├── ml/
├── docker/
└── docker-compose.yml
```

### FILE 1: PRD.md

```markdown
# VIXOR — Product Requirements Document

## 1. Problem
Security teams drown in raw, isolated scanner alerts. Static CVSS ignores asset sensitivity, exploit availability, auth barriers, and recurrence. Scanners give no explanation for severity, and every scan is independent, so teams cannot tell whether a vulnerability is new, recurring, or reintroduced. Commercial platforms are expensive.

## 2. Target Users
- Security Analyst: runs scans, triages findings, reads explanations.
- Administrator: manages users, roles, projects, audit logs.
- Management stakeholder (read-only): views executive summary and PDF reports.

## 3. Core Features (map to objectives)
- BO-1 Attack surface discovery: Subfinder + Certificate Transparency logs, DNS enumeration, live host detection, technology fingerprinting, asset inventory.
- BO-2 Unified scanning pipeline: Nuclei, OWASP ZAP, Nmap.
- BO-3 Contextual ML risk scoring (RandomForest + XGBoost).
- BO-4 Explainability: SHAP values + natural-language risk narratives.
- BO-5 Security correlation engine: groups related findings into attack narratives.
- BO-6 Regression intelligence: classifies each finding per scan cycle as NEW, RECURRING, REINTRODUCED, or RESOLVED.
- BO-7 Dashboard with real-time progress and visual analytics.
- BO-8 Professional PDF reports with risk summary and remediation guidance.
- BO-9 JWT auth, RBAC, audit logging.
- BO-10 Ethical scanning policy: ownership verification, scope enforcement, safe templates only.
- Scan scheduling (Celery Beat) and security posture trend tracking.

## 4. MVP Scope
IN: everything above for web apps, APIs, and subdomain infrastructure.
OUT: exploit execution, destructive pentesting, unauthorized targets, mobile apps, network-internal (non-internet-facing) scanning, multi-tenant billing.

## 5. User Stories & Acceptance Criteria
US-01 As an Analyst, I log in and receive a 15-min access token and a refresh cookie.
  AC: wrong password returns generic error; 5 failures in 10 min locks the account for 15 min; audit log entry written.
US-02 As an Admin, I create users and assign roles.
  AC: only Admin can hit /admin/*; Analyst gets 403; change is audit-logged.
US-03 As an Analyst, I create a project and register a domain.
  AC: domain starts as UNVERIFIED with a random token; scans are blocked until verified.
US-04 As an Analyst, I verify ownership via DNS TXT record (_vixor-verify.<domain>) or a file at /.well-known/vixor-verification.txt.
  AC: verification checks the exact token; success sets verified_at; failure gives a precise reason.
US-05 As an Analyst, I run discovery on a verified domain.
  AC: only subdomains ending in the verified root are stored; each asset has resolved IPs, live status, and detected technologies.
US-06 As an Analyst, I start a scan on selected assets.
  AC: scan rejected if asset out of scope or domain unverified; progress streams live; per-tool timeouts enforced.
US-07 As an Analyst, I view scored findings with an explanation.
  AC: each finding shows risk score 0-100, top 5 SHAP drivers, and a narrative sentence.
US-08 As an Analyst, I see regression status between scans.
  AC: finding fingerprint matched across scans; status is correct for NEW/RECURRING/REINTRODUCED/RESOLVED.
US-09 As an Analyst, I see correlated attack narratives.
  AC: e.g., exposed admin panel + outdated component + missing auth header are grouped with a combined narrative and combined risk.
US-10 As an Analyst/Management user, I download a PDF report.
  AC: includes executive summary, risk distribution, top findings with explanations, remediation guidance, regression trends.
US-11 As an Analyst, I schedule recurring scans (daily/weekly).
  AC: schedule persists; Celery Beat triggers; ownership re-verified before each scheduled run.

## 6. Edge Cases
- Domain token removed after verification: re-verification every 7 days; failure suspends scanning.
- Wildcard DNS returns IPs for any subdomain: detect and dedupe.
- Subdomain resolves to third-party/CDN/shared-hosting IP: flagged OUT_OF_SCOPE, never scanned.
- Scanner timeout or container crash: scan marked PARTIAL with reasons; other tools' results kept.
- Duplicate findings from multiple tools: deduplicated by fingerprint.
- ML model missing: scan completes with fallback rule-based score flagged "unscored by ML".
- Concurrent scans on same asset: queued, not parallel.
- Very large result sets: paginated APIs, streamed PDF generation.
```

### FILE 2: ARCHITECTURE.md

```markdown
# VIXOR — Architecture

## 1. Stack & Rationale
- FastAPI: async, typed, automatic OpenAPI, strong for APIs.
- PostgreSQL 15: relational integrity for assets/findings/history, JSONB for tool evidence and SHAP values.
- SQLAlchemy 2.0 + Alembic: typed ORM and versioned migrations.
- Redis 7: Celery broker/result backend, pub/sub for live scan progress, rate-limit counters.
- Celery + Beat: async scan pipeline, scheduling, retries, timeouts.
- Next.js 14 App Router (React 18) + TypeScript + Tailwind + Recharts + Zod: middleware-protected routes, dashboard UI.
- Scanner containers: Subfinder, httpx, Nmap, ZAP (daemon + API), Nuclei isolated from the API container; worker invokes them via a restricted wrapper.
- scikit-learn, XGBoost, SHAP: models and explanations. ReportLab (or WeasyPrint) for PDFs.

## 2. Directory Structure
backend/
  app/
    main.py, config.py, deps.py
    core/ (security.py, rbac.py, rate_limit.py, logging.py)
    models/ (user, audit_log, project, domain, asset, scan, finding, finding_score, finding_history, correlation, report, schedule)
    schemas/ (Pydantic models per resource)
    api/v1/ (auth, users, projects, domains, assets, scans, findings, correlations, reports, dashboard, ws)
    services/
      auth_service.py, audit_service.py, project_service.py
      domain_verification.py, scope_guard.py
      discovery/ (subfinder, ct_logs, dns_enum, httpx_probe)
      scanning/ (nmap_runner, zap_runner, nuclei_runner, normalizer, orchestrator)
      ml/ (features.py, scoring.py, explain.py, narrative.py)
      correlation_engine.py, regression_engine.py, report_service.py
    workers/ (celery_app.py, tasks_discovery.py, tasks_scan.py, tasks_ml.py, tasks_schedule.py)
  alembic/, tests/ (unit, integration), requirements.txt, Dockerfile
ml/
  data/ (fetch_nvd.py, fetch_epss.py, fetch_kev.py, build_dataset.py)
  training/ (train_rf.py, train_xgb.py, evaluate.py)
  artifacts/ (model files + metadata.json, gitignored)
frontend/
  src/app/ (login, dashboard, projects/[id], domains, assets, scans/[id], findings/[id], correlations, reports, admin/users, admin/audit)
  src/components/, src/lib/ (api client, zod schemas, auth), src/middleware.ts
docker/ (api.Dockerfile, worker.Dockerfile, web.Dockerfile, scanner-tools.Dockerfile)

## 3. Data Flow
1. Analyst registers domain -> token issued -> DNS TXT/file verification -> verified_at set.
2. Discovery task: Subfinder + CT logs + DNS enumeration -> scope_guard filters (suffix match, IP resolution, CDN/shared-hosting blocklist) -> httpx probe (live, status, tech) -> assets stored.
3. Scan task (per asset): scope_guard re-check -> Nmap (service detection) -> ZAP (active scan, non-destructive policy) -> Nuclei (safe templates) -> normalizer converts each tool's output to a unified Finding schema -> dedupe by fingerprint.
4. ML task: feature extraction -> RF/XGBoost risk score -> SHAP values -> deterministic narrative.
5. Regression engine: compare fingerprints with previous scans -> set status.
6. Correlation engine: group findings per asset/host by rules + shared attributes -> attack narrative with combined score.
7. Progress events published to Redis pub/sub -> WebSocket -> dashboard.
8. Report service renders PDF from stored data.

## 4. Scope Guard Rules (LI-1, BO-10)
- Domain must have verified_at within last 7 days.
- Asset hostname must equal or be a subdomain of verified root.
- All resolved IPs must not be in private ranges (unless explicitly allowed by Admin in lab mode), cloud metadata IPs, or known CDN/shared hosting ranges; those assets are OUT_OF_SCOPE.
- Enforced in API layer AND at the start of every scanner task.
- Nuclei: exclude tags dos, intrusive, fuzz, bruteforce. ZAP: attack strength LOW/MEDIUM, no destructive rules. Nmap: -sV with safe scripts only, no exploit scripts.
- LI-4: per-tool timeouts, per-project concurrency of 2, global rate limits, container CPU/memory caps.

## 5. ML Design
Features: cvss_base, epss_score, in_cisa_kev, exploit_available, asset_sensitivity (derived from tech/path heuristics: admin, login, API, payment), internet_exposed, auth_required, service_port_risk, tool_confidence, template_severity, age_of_cve_days, recurrence_count (from regression history), detected_tech_outdated.
Labels: no ground truth exists. Build a documented weak-supervision label: priority class (Low/Medium/High/Critical) from a transparent rule blend of KEV membership, EPSS percentile, CVSS, and exposure, with noise added and an held-out split by CVE to avoid leakage. Document honestly that models learn contextual prioritization, and report accuracy, macro-F1, and calibration. Models are versioned in ml/artifacts with metadata.json.
Explainability: SHAP TreeExplainer on the winning model; top-5 contributions stored in finding_scores.shap_values; narrative generated from templates (e.g., "Risk is high mainly because this CVE is in CISA KEV (+18) and the asset exposes an admin login (+12)").

## 6. Database Schema (PostgreSQL)
users(id uuid pk, email unique, password_hash, role enum[admin,analyst,viewer], is_active, failed_attempts, locked_until, created_at)
audit_logs(id, user_id fk null, action, resource_type, resource_id, ip, user_agent, metadata jsonb, created_at)
projects(id, owner_id fk, name, description, created_at)
domains(id, project_id fk, root_domain, verification_token, verification_method enum[dns_txt,file], status enum[unverified,verified,suspended], verified_at, last_reverified_at, created_at; unique(project_id, root_domain))
assets(id, domain_id fk, hostname, ips jsonb, is_live, scope_status enum[in_scope,out_of_scope], scope_reason, technologies jsonb, sensitivity_score, first_seen, last_seen; unique(domain_id, hostname))
scans(id, project_id fk, domain_id fk, triggered_by fk, status enum[queued,running,partial,completed,failed], started_at, finished_at, error_summary)
scan_assets(scan_id fk, asset_id fk, status)
findings(id, asset_id fk, scan_id fk, fingerprint, source_tool enum[nmap,zap,nuclei], title, description, severity_raw, cvss, cve_ids jsonb, evidence jsonb, remediation text, created_at; index(fingerprint))
finding_scores(finding_id pk fk, risk_score float, risk_class, model_version, features jsonb, shap_values jsonb, narrative text, scored_by enum[ml,fallback])
finding_history(id, fingerprint, asset_id fk, scan_id fk, status enum[new,recurring,reintroduced,resolved])
correlations(id, scan_id fk, asset_id fk, title, narrative, combined_score, finding_ids jsonb)
reports(id, scan_id fk, generated_by fk, file_path, created_at)
scan_schedules(id, domain_id fk, cron, is_active, last_run_at)

## 7. API Spec (prefix /api/v1; all except /auth/login require JWT)
POST /auth/login | POST /auth/refresh | POST /auth/logout
GET/POST /users, PATCH /users/{id} (admin)
GET/POST /projects, GET/PATCH/DELETE /projects/{id}
POST /projects/{id}/domains | POST /domains/{id}/verify | GET /domains/{id}
POST /domains/{id}/discover | GET /domains/{id}/assets
POST /scans | GET /scans/{id} | GET /scans/{id}/findings
GET /findings/{id} | GET /scans/{id}/correlations | GET /domains/{id}/regression
POST /scans/{id}/report | GET /reports/{id}/download
GET /dashboard/summary | GET /dashboard/trends
POST/GET/DELETE /domains/{id}/schedules
GET /admin/audit-logs (admin) | WS /ws/scans/{id}
All list endpoints are paginated. All inputs validated with Pydantic. Ownership checks on every resource (IDOR protection).
```

### FILE 3: RULES.md

```markdown
# VIXOR — Engineering Rules

1. One atomic task per commit. Conventional commits (feat:, fix:, chore:, test:, docs:, refactor:).
2. No dead code, no commented-out code, no unused imports. Linters (ruff, mypy strict on services, eslint, tsc) must pass.
3. Every endpoint: Pydantic request/response models, explicit status codes, RBAC dependency, ownership check, audit log on state change.
4. Every UI view: loading, empty, error, and success states. No unhandled promise rejections.
5. Never trust input. Validate on the backend (Pydantic) and the frontend (Zod).
6. Never shell-interpolate user input. Scanner commands use argument lists with subprocess (shell=False) and allowlisted flags only.
7. Secrets only via environment variables. Never log secrets, tokens, or password hashes.
8. All scanning code must call scope_guard before touching a target. No exceptions.
9. Never use an LLM for risk scoring. Narratives are deterministic templates.
10. DB changes only through Alembic migrations. Never edit applied migrations.
11. Tests required for every service function: unit tests for logic, integration tests for API, mocked scanner outputs (never hit real targets in tests).
12. Type hints everywhere in Python; strict TypeScript.
13. Keep functions small and single-purpose; services hold logic, routers stay thin.
14. Dependencies pinned to exact versions.
15. Update MEMORY.md after every task.
```

### FILE 4: DESIGN.md

```markdown
# VIXOR — Design System

Theme: premium dark luxury, security-operations aesthetic, mobile-first.
Palette: background #07090D, surface #0E131B, elevated #151C27, border #1F2937, text #E6EDF3, muted #8B98A9, primary (electric cyan) #22D3EE, accent (amber) #F5B83D.
Severity colors: critical #F43F5E, high #F97316, medium #F5B83D, low #38BDF8, info #94A3B8.
Typography: Inter for UI, JetBrains Mono for hostnames, evidence, and code. Scale 12/14/16/20/28/40.
Components: Card with subtle border and glow on hover, StatCard, SeverityBadge, DataTable (sortable, paginated, sticky header), ScanProgress (live stepper), RiskGauge (0-100), ShapBarChart (horizontal, positive/negative colors), TrendLineChart, AssetGraph (simple tree), Toast, Modal, EmptyState, Skeleton loaders.
Layout: sidebar (collapsible) on desktop, bottom tab bar on mobile. Breakpoints 360 / 768 / 1024 / 1440. Touch targets minimum 44px.
Motion: 150-200ms ease, no heavy animation, respect prefers-reduced-motion.
Accessibility: WCAG AA contrast, keyboard navigation, aria labels on charts.
```

### FILE 5: TASKS.md

```markdown
# VIXOR — Tasks (execute top to bottom)

## Setup
[ ] T-001 Init git repo, .gitignore, .editorconfig, pre-commit (ruff, eslint, gitleaks)
[ ] T-002 Backend skeleton: FastAPI app, config via pydantic-settings, /health, structured JSON logging
[ ] T-003 docker-compose: api, worker, beat, web, postgres, redis, zap, scanner-tools with healthchecks and resource limits
[ ] T-004 Alembic setup and base migration; pytest skeleton with test DB fixture
[ ] T-005 Next.js 14 App Router skeleton with TypeScript, Tailwind, design tokens from DESIGN.md

## Security Foundation
[ ] T-006 Password hashing (argon2), JWT access (15m) + refresh (httpOnly, Secure, SameSite=Strict cookie, rotation)
[ ] T-007 RBAC dependency (admin/analyst/viewer) + tests
[ ] T-008 Audit logging service + middleware + /admin/audit-logs
[ ] T-009 Rate limiting (Redis) on auth and scan endpoints; account lockout
[ ] T-010 Security headers, CORS allowlist, request size limits

## Database
[ ] T-011 Models and migrations for users, audit_logs, projects, domains
[ ] T-012 Models and migrations for assets, scans, scan_assets, findings
[ ] T-013 Models and migrations for finding_scores, finding_history, correlations, reports, scan_schedules
[ ] T-014 Seed script: admin user from env, demo project with fixture data (dev only)

## Core Features
[ ] T-015 Auth endpoints + tests
[ ] T-016 Users admin endpoints + tests
[ ] T-017 Projects CRUD with ownership checks
[ ] T-018 Domain registration + token generation
[ ] T-019 Domain verification (DNS TXT + file) + periodic re-verification task
[ ] T-020 scope_guard service (suffix, IP resolution, CDN/shared-host blocklist, private range block) + exhaustive tests
[ ] T-021 Discovery: Subfinder runner
[ ] T-022 Discovery: CT log client (crt.sh) with caching and timeouts
[ ] T-023 Discovery: DNS enumeration + wildcard detection
[ ] T-024 Discovery: httpx probe (live hosts, technology fingerprinting)
[ ] T-025 Discovery Celery task + asset inventory API
[ ] T-026 Nmap runner (safe flags, XML parsing) + normalizer
[ ] T-027 ZAP runner (non-destructive policy, API client) + normalizer
[ ] T-028 Nuclei runner (excluded tags, JSONL parsing) + normalizer
[ ] T-029 Scan orchestrator: Celery chain, timeouts, retries, partial-failure handling, per-project concurrency
[ ] T-030 Finding dedupe by fingerprint
[ ] T-031 Redis pub/sub progress + WebSocket endpoint (auth required)
[ ] T-032 ML data: fetch NVD, EPSS, CISA KEV; build_dataset with documented labeling strategy
[ ] T-033 ML training: RandomForest + XGBoost, evaluation report, versioned artifacts
[ ] T-034 Feature extraction service for live findings
[ ] T-035 Scoring service + fallback rule-based scorer
[ ] T-036 SHAP explanations + deterministic narrative generator
[ ] T-037 Regression engine (NEW/RECURRING/REINTRODUCED/RESOLVED) + tests
[ ] T-038 Correlation engine (rule-based grouping + combined score + narrative) + tests
[ ] T-039 Dashboard summary and trend endpoints
[ ] T-040 PDF report service (exec summary, charts, findings, remediation, regression)
[ ] T-041 Scan scheduling with Celery Beat (re-verify ownership before each run)

## UI
[ ] T-042 Login page, auth context, middleware route protection
[ ] T-043 App shell: sidebar/bottom tabs, role-aware navigation
[ ] T-044 Projects and domains pages with verification wizard
[ ] T-045 Assets inventory page
[ ] T-046 Scan launch + live progress page
[ ] T-047 Findings list and detail (risk gauge, SHAP chart, narrative, remediation)
[ ] T-048 Correlations and regression views
[ ] T-049 Dashboard (stats, severity distribution, trends) + executive summary view
[ ] T-050 Reports page + download
[ ] T-051 Admin: users and audit log pages

## Testing
[ ] T-052 Unit tests: scope_guard, regression, correlation, feature extraction
[ ] T-053 Integration tests: auth, RBAC, IDOR, scan flow with mocked scanners
[ ] T-054 E2E tests (Playwright): login, verify domain, run mocked scan, view findings, download report
[ ] T-055 Load/limit tests: concurrency and timeout behavior (LI-4)
[ ] T-056 Final security checklist verification and completion report
```

### FILE 6: MEMORY.md

```markdown
# VIXOR — Memory

## Active State
Current task: T-001
Last completed: none

## Required Environment Variables
See security/secrets.md

## Architectural Decisions
- Next.js 14 App Router chosen as React 18 framework.
- LLMs never used for scoring; narratives are template-based.
- Weak-supervision labels for ML (no ground truth); documented in ARCHITECTURE.md.

## Known Issues

## Technical Debt Log
```

### FILE 7: security/threat-model.md

```markdown
# VIXOR — STRIDE Threat Model

Spoofing: stolen JWT, credential stuffing, fake domain ownership claims. Mitigate: short-lived tokens, refresh rotation, lockout, rate limits, token-based ownership proof with periodic re-verification.
Tampering: modified scan results, tampered ML artifacts, altered audit logs. Mitigate: DB constraints, append-only audit table (no update/delete grants), artifact checksum validation at load.
Repudiation: user denies launching a scan. Mitigate: audit logs for every state change with user, IP, timestamp.
Information Disclosure: IDOR on projects/findings/reports, secrets in client, verbose errors, PDF access by URL guessing. Mitigate: ownership checks, no secrets client-side, generic errors, authenticated report downloads with random IDs.
Denial of Service: scan flooding, huge targets, scanner resource exhaustion. Mitigate: rate limits, concurrency caps, timeouts, container limits, pagination.
Elevation of Privilege: analyst reaching admin routes, command injection via domain names into scanner CLIs. Mitigate: RBAC on every route, strict hostname regex validation, shell=False with allowlisted args.
Platform-specific abuse: using VIXOR to attack third parties. Mitigate: ownership verification, scope_guard (suffix, IP, CDN/shared-host blocks), safe templates only, audit trail.
SSRF: scanner or report features reaching internal services. Mitigate: block private/metadata IPs, scanners in isolated network, egress rules.
```

### FILE 8: security/attack-surface.md

```markdown
# VIXOR — Attack Surface Inventory

Public endpoints: POST /auth/login, POST /auth/refresh.
Authenticated endpoints: every route listed in ARCHITECTURE.md section 7.
Admin-only: /users, /admin/audit-logs.
WebSocket: /ws/scans/{id} (JWT validated on connect, ownership checked).
User inputs: email/password, project name/description, root domain, verification method, asset selection, scan options, schedule cron expressions, report requests.
High-risk inputs: domain/hostname (command-injection and SSRF vector), cron expression (validate against allowlist presets), uploaded nothing (no file uploads in MVP).
Outbound calls: crt.sh, NVD, EPSS, CISA KEV (fetched by offline ML scripts, not at request time), DNS queries, target HTTP/TCP via scanners.
Auth surfaces: access JWT in Authorization header, refresh token httpOnly cookie, Next.js middleware cookie checks.
Containers: api, worker, beat, web, postgres, redis, zap, scanner-tools. Only web and api exposed through the reverse proxy; postgres, redis, zap internal only.
File system: report PDFs and ML artifacts (not publicly served).
```

### FILE 9: security/secrets.md

```markdown
# VIXOR — Secrets & Environment Variables

.env.example:
DATABASE_URL=postgresql+psycopg://vixor:change_me@postgres:5432/vixor
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=generate_with_openssl_rand_hex_64
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
COOKIE_SECURE=true
CORS_ALLOWED_ORIGINS=https://localhost:3000
ADMIN_EMAIL=admin@example.com
ADMIN_INITIAL_PASSWORD=change_me_on_first_login
ZAP_API_KEY=generate_with_openssl_rand_hex_32
ZAP_API_URL=http://zap:8090
SCAN_TOOL_TIMEOUT_SECONDS=1800
MAX_CONCURRENT_SCANS_PER_PROJECT=2
REVERIFY_INTERVAL_DAYS=7
ALLOW_PRIVATE_IP_SCANNING=false
NEXT_PUBLIC_API_BASE_URL=https://localhost:8000/api/v1

Rules: only NEXT_PUBLIC_API_BASE_URL may be exposed to the browser. Rotate JWT_SECRET_KEY and ZAP_API_KEY every 90 days or on suspected leak; rotating JWT key invalidates sessions. Never commit .env. gitleaks runs in pre-commit and CI.
```

### FILE 10: security/security-checklist.md

```markdown
# VIXOR — 6-Pillar Security Checklist

## 1. Authentication & Sessions
[ ] argon2 hashing [ ] 15-min access tokens [ ] refresh rotation + revocation on logout [ ] lockout and rate limit [ ] generic login errors
## 2. Authorization & IDOR
[ ] RBAC on all routes [ ] ownership check on every resource query [ ] tests proving cross-user access returns 404/403
## 3. Hardened Deployment & Audit
[ ] TLS via reverse proxy [ ] security headers (CSP, HSTS, X-Frame-Options, nosniff) [ ] internal-only DB/Redis/ZAP [ ] structured audit logs, append-only [ ] non-root containers with resource limits
## 4. Abuse Prevention
[ ] rate limits per user/IP [ ] scan concurrency caps [ ] ownership verification enforced [ ] scope_guard enforced in API and workers [ ] safe-template-only scanning
## 5. Zero Secrets in Client
[ ] only NEXT_PUBLIC_API_BASE_URL public [ ] gitleaks clean [ ] no secrets in logs or error messages [ ] tokens never in localStorage
## 6. Input Validation & Injection Defense
[ ] Pydantic + Zod on all inputs [ ] hostname regex validation [ ] subprocess shell=False with allowlisted flags [ ] parameterized queries only [ ] output encoding in UI and PDF
```
```

---

## PART 2: THE 8 VIBE CODING STAGE PROMPTS

### Stage 1: Idea -> PRD Validation
```
Read PRD.md and the VIXOR scope: modules Authentication & RBAC, Attack Surface Discovery, Vulnerability Scanning, AI/XAI Engine, Dashboard & Reporting, plus Correlation and Regression Intelligence.
Validate that every objective BO-1 to BO-10 and every limitation LI-1 to LI-4 maps to at least one user story with acceptance criteria. List any gap, ambiguity, or contradiction. Fix gaps directly in PRD.md, keeping scope limited to web apps, APIs, and subdomain infrastructure. Do not add features outside the scope document. Log changes in MEMORY.md. Do not ask me questions; choose the safest option.
```

### Stage 2: PRD -> Tech Stack Verification
```
Verify the stack in ARCHITECTURE.md against PRD.md: FastAPI + SQLAlchemy 2 + Alembic, PostgreSQL 15, Redis, Celery + Beat, Next.js 14 App Router (React 18), Tailwind, Recharts, Zod, Subfinder, httpx, Nmap, OWASP ZAP, Nuclei, scikit-learn, XGBoost, SHAP.
For each component confirm: it satisfies a PRD requirement, a stable pinned version exists, and it runs in Docker. Check compatibility (Python 3.11, Node 20 LTS, XGBoost/SHAP versions). Replace anything unjustified or incompatible, update ARCHITECTURE.md and requirements/package files, and record the reasoning in MEMORY.md.
```

### Stage 3: Architecture & Data Flow Sign-off
```
Review ARCHITECTURE.md end to end. Trace these flows step by step and confirm each hop has an owner module, input validation, error handling, and an audit log where state changes: (1) domain registration -> verification -> discovery -> asset inventory, (2) scan request -> scope_guard -> Nmap/ZAP/Nuclei -> normalization -> dedupe -> ML scoring -> SHAP -> regression -> correlation -> report, (3) scheduled scan with ownership re-verification.
Specifically verify that scope_guard is enforced both in the API and inside each Celery task, that scanners run with non-destructive settings, and that LLMs are never in the scoring path. Fix any weakness in the document and log the sign-off in MEMORY.md.
```

### Stage 4: Database Migration & Seed Generation
```
Implement T-011 to T-014. Create SQLAlchemy 2.0 models and Alembic migrations for every table in ARCHITECTURE.md section 6, including enums, foreign keys with ON DELETE rules, unique constraints (domains: project_id+root_domain; assets: domain_id+hostname), and indexes (findings.fingerprint, assets.domain_id, audit_logs.created_at). Make audit_logs append-only by revoking UPDATE/DELETE from the application DB role in the migration. Write the seed script: create the admin user from ADMIN_EMAIL/ADMIN_INITIAL_PASSWORD (argon2), and in development only, a demo project with a fixture domain and sample findings. Add tests that migrations apply and roll back cleanly on an empty DB. Tick tasks and log in MEMORY.md.
```

### Stage 5: Feature Build (Feature #1: Domain Ownership Verification and Scope Guard)
```
Implement T-018, T-019, T-020 as Feature #1.
Requirements: POST /projects/{id}/domains creates a domain with a cryptographically random verification token (secrets.token_urlsafe(32)), status UNVERIFIED. POST /domains/{id}/verify supports method dns_txt (TXT at _vixor-verify.<root_domain> equal to the token) and file (GET https://<root>/.well-known/vixor-verification.txt containing the token; follow no redirects to other hosts; 5s timeout; block private IPs to prevent SSRF). On success set status VERIFIED and verified_at. A Celery Beat task re-verifies every REVERIFY_INTERVAL_DAYS and sets SUSPENDED on failure. Implement scope_guard.is_in_scope(domain, hostname): hostname must equal or end with ".<root_domain>", all resolved IPs must be public, not cloud-metadata, not in the CDN/shared-hosting blocklist; return a reason string for audit logs. Strict hostname regex validation. Ownership checks (IDOR) on all routes, audit logs on all state changes, Pydantic schemas.
Write unit tests (including adversarial hostnames like evil.com?.victim.com, trailing dots, unicode homographs, IPs as hostnames) and integration tests with mocked DNS/HTTP. Run everything, tick tasks, log in MEMORY.md.
HOW TO LOOP FOR NEXT FEATURES: after completing a feature, run Stage 6 (review), Stage 7 (tests), then the relevant Part 3 security prompt, then take the next unticked feature group in TASKS.md and repeat this Stage 5 template, replacing the task IDs and requirements with the next group's.
```

### Stage 6: Senior Code Review
```
Act as a senior security-minded code reviewer on the code changed since the last review (git diff against the last review commit noted in MEMORY.md). For each issue output: PROBLEM (file:line) -> WHY it matters (security, correctness, performance, maintainability) -> FIX (concrete code change). Prioritize: scope_guard bypasses, command/argument injection in scanner runners, IDOR, missing audit logs, missing error/loading states, N+1 queries, untested branches, dead code. Apply all High and Medium fixes directly, re-run tests, and list Low items in MEMORY.md technical debt. Record the review commit hash in MEMORY.md.
```

### Stage 7: Automated Test Suite
```
Write and run tests for the latest feature, following RULES.md rule 11. Unit tests (pytest): pure logic such as scope_guard, fingerprinting, regression classification, correlation rules, feature extraction, narrative generation. Integration tests (pytest + httpx AsyncClient + test DB): every endpoint with success, validation failure, unauthenticated, wrong-role, and cross-user (IDOR) cases; scanner runners against recorded sample outputs (nmap XML, ZAP JSON, nuclei JSONL), never real targets. E2E (Playwright) for UI flows once relevant. Target at least 85% coverage on services/. Fix any failing code (not the tests) unless the test is wrong; document in MEMORY.md.
```

### Stage 8: Root-Cause Debugger
```
A bug exists. Do not guess. Produce: EXPECTED behavior (cite PRD acceptance criteria) vs ACTUAL behavior (exact error, logs, reproduction steps) vs ROOT CAUSE (trace through the code with evidence). Write a failing test that reproduces it first. Apply the MINIMAL fix touching the fewest lines, confirm the new test passes and the full suite stays green, and add a regression note to MEMORY.md. Do not refactor unrelated code.
```

---

## PART 3: THE 6 SECURITY ENFORCEMENT PROMPTS

### Security 1: Secure Authentication & Session Lifecycle
```
Implement and audit T-006 to T-009 and T-015. Use argon2id (argon2-cffi) for password hashing. Access JWT lifetime 15 minutes (claims: sub, role, jti, exp, iat); refresh token is opaque, stored hashed in the DB, sent as httpOnly + Secure + SameSite=Strict cookie, rotated on every refresh with reuse detection (reuse revokes the whole token family). Logout revokes the refresh token. Login: generic error messages, constant-time comparison, account lockout after 5 failures in 10 minutes for 15 minutes, per-IP rate limiting in Redis. Next.js middleware must protect all routes except /login and verify role for /admin. Never store tokens in localStorage. Audit-log login success, failure, lockout, logout, refresh reuse. Add tests for each rule.
```

### Security 2: IDOR Prevention & Row-Level Data Ownership
```
Audit every route in ARCHITECTURE.md section 7. Every query touching projects, domains, assets, scans, findings, correlations, reports, schedules must be scoped through the owning project (admins may see all, with audit logging of the access). Implement a reusable dependency/repository pattern (get_owned_or_404) so no router queries by raw ID. Return 404 (not 403) for resources the user does not own. Make report download IDs unguessable (UUID4) and still ownership-checked. Protect the WebSocket the same way. Write a parametrized test that iterates every route with a second user's resource IDs and asserts denial. Fix all gaps.
```

### Security 3: Hardened Deployment, TLS & Structured Audit Logging
```
Harden docker-compose and deployment (T-003, T-008, T-010): reverse proxy (Caddy or nginx) terminating TLS, HTTP -> HTTPS redirect, HSTS; security headers (CSP without unsafe-inline, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy); strict CORS allowlist; non-root users in all Dockerfiles; read-only filesystems where possible; CPU/memory limits (LI-4); postgres, redis, zap on an internal-only network with no published ports; scanner containers on an isolated network with egress only to scan targets, blocking RFC1918 and cloud metadata ranges. Structured JSON logging with request IDs; audit_logs append-only at DB level; never log secrets or tokens. Add a health-check test and a script that verifies headers on every response.
```

### Security 4: Abuse Prevention, Rate Limiting & Bot Protection
```
Implement abuse controls for VIXOR, which could be misused to attack third parties: (1) Redis sliding-window rate limits on /auth/*, scan creation, discovery, verification, and report generation, per user and per IP; (2) max 2 concurrent scans per project, global queue cap, per-tool timeouts and retries with backoff (LI-4); (3) scan blocked unless domain VERIFIED within the re-verification window and scope_guard passes, enforced in the API and again at the top of every Celery task; (4) Nuclei excluded tags dos, intrusive, fuzz, bruteforce, ZAP policy LOW/MEDIUM strength non-destructive, Nmap safe scripts only; (5) CAPTCHA-ready hook on login after repeated failures; (6) alert and auto-suspend a user or domain after repeated scope_guard violations. Test every limit and the scope rejection paths.
```

### Security 5: Zero Secrets in Client & Secret Scanning
```
Ensure no secret can reach the browser or git. Only NEXT_PUBLIC_API_BASE_URL may be public in the Next.js app; add a CI/test check that fails if any other NEXT_PUBLIC_ variable exists or if server-only env names appear in the client bundle (grep the .next build output). Configure gitleaks in pre-commit and CI with a custom rule for JWT_SECRET_KEY and ZAP_API_KEY patterns. Validate settings at startup (pydantic-settings) and refuse to start with default or placeholder secrets in production mode. Verify .env is gitignored and .env.example contains placeholders only. Sanitize error responses and logs so they never include tokens, hashes, or stack traces to clients. Run gitleaks over full git history and report.
```

### Security 6: Input Sanitization, Zod Validation & Injection Defense
```
Harden all inputs. Backend: Pydantic models with strict types and length limits on every request; hostname/domain regex (RFC-compliant labels, no underscores except the verification record, no IPs, no ports, no schemes); cron input restricted to allowlisted presets (daily, weekly); enums for all choices. Scanner runners: subprocess with shell=False, argument lists only, allowlisted flags, hostname passed as a single validated argument, no user-controlled flags or template paths. SQL: SQLAlchemy parameterized queries only. Output: escape evidence/titles/descriptions from scanners (they contain attacker-controlled text) in the React UI (no dangerouslySetInnerHTML) and sanitize in PDF generation. Frontend: Zod schemas mirroring backend models for every form and for API responses. Add fuzz-style tests with injection payloads (command, SQL, XSS, path traversal, SSRF URLs) for each endpoint and runner.
```

---

## PART 4: AUTONOMOUS EXECUTION ROADMAP

**Phase A: Scaffolding.** Paste Part 0 into OpenCode, then Part 1. Result: docs and folders committed. Run Stage 1, 2, 3 to validate PRD, stack, and architecture (T-001 to T-005).

**Phase B: Database & Auth.** Stage 4 (T-011 to T-014), then Security 1, 2, 3 and 6 for the foundation (T-006 to T-010, T-015, T-016). Gate: login, RBAC, IDOR, and audit tests green.

**Phase C: Feature Iteration Loop.** For each feature group below, run Build (Stage 5 template) -> Review (Stage 6) -> Test (Stage 7) -> Security Check (relevant Part 3 prompt + checklist pillars). Debug with Stage 8 when needed.
1. Projects, domain registration, ownership verification, scope_guard (T-017 to T-020) -> Security 4 and 6
2. Discovery: Subfinder, CT logs, DNS, httpx (T-021 to T-025) -> Security 6
3. Scanning pipeline: Nmap, ZAP, Nuclei, orchestrator, dedupe, live progress (T-026 to T-031) -> Security 4 and 6
4. ML dataset, training, scoring, SHAP, narratives (T-032 to T-036). Pause point: review the evaluation report honestly before continuing.
5. Regression and correlation engines (T-037, T-038)
6. Dashboard APIs, PDF reports, scheduling (T-039 to T-041) -> Security 2 and 4
7. UI pages (T-042 to T-051) -> Security 5

**Phase D: Production Hardening.** Security 3 and 5 full pass, remaining testing tasks (T-052 to T-055: E2E, limits, concurrency), run the entire security checklist, fix findings, then T-056 completion report. Final deliverables: green CI, all tasks ticked, MEMORY.md up to date, demo with a domain you own.

**Practical advice for your viva:** demo only on a domain you control (for example a lab domain or a deliberately vulnerable app like OWASP Juice Shop running on your own subdomain), and show the ownership-verification step blocking an unverified target.
