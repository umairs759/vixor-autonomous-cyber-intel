# VIXOR — Tasks (execute top to bottom)

## Setup
[x] T-001 Init git repo, .gitignore, .editorconfig, pre-commit (ruff, eslint, gitleaks)
[x] T-002 Backend skeleton: FastAPI app, config via pydantic-settings, /health, structured JSON logging
[x] T-003 docker-compose: api, worker, beat, web, postgres, redis, zap, scanner-tools with healthchecks and resource limits
[x] T-004 Alembic setup and base migration; pytest skeleton with test DB fixture
[x] T-005 Next.js 14 App Router skeleton with TypeScript, Tailwind, design tokens from DESIGN.md

## Security Foundation
[ ] T-006 Password hashing (argon2), JWT access (15m) + refresh (httpOnly, Secure, SameSite=Strict cookie, rotation) — refresh flow corrected; end-to-end API verification pending.
[x] T-007 RBAC dependency (admin/analyst/viewer) + tests
[x] T-008 Audit logging service + middleware + /admin/audit-logs
[x] T-009 Rate limiting (Redis) on auth and scan endpoints; account lockout
[x] T-010 Security headers, CORS allowlist, request size limits

## Database
[x] T-011 Models and migrations for users, audit_logs, projects, domains
[x] T-012 Models and migrations for assets, scans, scan_assets, findings
[x] T-013 Models and migrations for finding_scores, finding_history, correlations, reports, scan_schedules
[x] T-014 Seed script: admin user from env, demo project with fixture data (dev only)

## Core Features
[ ] T-015 Auth endpoints + tests — signed refresh rotation and HttpOnly cookies implemented; endpoint verification pending.
[x] T-016 Users admin endpoints + tests
[ ] T-017 Projects CRUD with ownership checks — API authentication/ownership regression tests added; runtime verification blocked by Windows asyncio socket-pair hang in TestClient.
[x] T-018 Domain registration + token generation
[x] T-019 Domain verification (DNS TXT + file) + periodic re-verification task
[x] T-020 scope_guard service (suffix, IP resolution, CDN/shared-host blocklist, private range block) + exhaustive tests
[x] T-021 Discovery: Subfinder runner
[x] T-022 Discovery: CT log client (crt.sh) with caching and timeouts
[x] T-023 Discovery: DNS enumeration + wildcard detection
[x] T-024 Discovery: httpx probe (live hosts, technology fingerprinting)
[x] T-025 Discovery Celery task + asset inventory API
[x] T-026 Nmap runner (safe flags, XML parsing) + normalizer
[x] T-027 ZAP runner (non-destructive policy, API client) + normalizer
[x] T-028 Nuclei runner (excluded tags, JSONL parsing) + normalizer
[ ] T-029 Scan orchestrator: Celery chain, timeouts, retries, partial-failure handling, per-project concurrency ? per-project concurrency cap still needs enforcement and verification.
[x] T-030 Finding dedupe by fingerprint
[x] T-031 Redis pub/sub progress + WebSocket endpoint (auth required)
[x] T-032 ML data: fetch NVD, EPSS, CISA KEV; build_dataset with documented labeling strategy
[x] T-033 ML training: RandomForest + XGBoost, evaluation report, versioned artifacts
[x] T-034 Feature extraction service for live findings
[x] T-035 Scoring service + fallback rule-based scorer
[x] T-036 SHAP explanations + deterministic narrative generator
[x] T-037 Regression engine (NEW/RECURRING/REINTRODUCED/RESOLVED) + tests
[x] T-038 Correlation engine (rule-based grouping + combined score + narrative) + tests
[x] T-039 Dashboard summary and trend endpoints
[x] T-040 PDF report service (exec summary, charts, findings, remediation, regression)
[ ] T-041 Scan scheduling with Celery Beat ? cron validation and due-time dispatch implemented; full broker/worker integration remains unverified.

## UI
[ ] T-042 Login page, auth context, middleware route protection — middleware moved to Next 14 registered path and JWT signature validation added; fresh build blocked by EPERM creating generated output directories under the managed filesystem ACL.
[x] T-043 App shell: sidebar/bottom tabs, role-aware navigation
[x] T-044 Projects and domains pages with verification wizard
[x] T-045 Assets inventory page
[x] T-046 Scan launch + live progress page
[x] T-047 Findings list and detail (risk gauge, SHAP chart, narrative, remediation)
[x] T-048 Correlations and regression views
[x] T-049 Dashboard (stats, severity distribution, trends) + executive summary view
[ ] T-050 Reports page + download ? UI and PDF ownership/file checks implemented; report service and browser download need end-to-end verification.
[x] T-051 Admin: users and audit log pages

## Testing
[x] T-052 Unit tests: scope_guard, regression, correlation, feature extraction
[x] T-053 Integration tests: auth, RBAC, IDOR, scan flow with mocked scanners
[ ] T-054 E2E tests (Playwright): login, verify domain, run mocked scan, view findings, download report ? not re-run in this environment.
[ ] T-055 Load/limit tests: concurrency and timeout behavior (LI-4) ? concurrency cap remains incomplete.
[ ] T-056 Final security checklist verification and completion report ? final review records remaining blocked items.
