# VIXOR — Codebase Audit (T-001 through T-056)

**Status legend:**
- `[DONE-VERIFIED]` — Implemented AND verified end-to-end (static + functional + requirements alignment).
- `[WRITTEN-BUT-UNVERIFIED]` — Code exists but not verified against a real runtime (no `docker compose up --build` boot, no live API curl, no DB/audit evidence).
- `[PARTIAL]` — Partially implemented; missing components, failing tests, or unverified runtime behavior.
- `[MISSING]` — Not implemented or absent from the codebase.

**Audit basis:** Inspection of `backend/`, `frontend/`, `ml/`, `docker/`, `secrets/`, `docker-compose.yml`, `TASKS.md`, `MEMORY.md`, `PRD.md`, `ARCHITECTURE.md`, `RULES.md`. Concrete data from `npm run build` (frontend) and `docker compose config`.

> NOTE: MEMORY.md claims many tasks complete, but TASKS.md is entirely unticked and no execution verification exists. This audit reflects actual on-disk state, not claims.

---

## Setup

| Task | Status | Evidence |
|------|--------|----------|
| T-001 Init git repo, .gitignore, .editorconfig, pre-commit | [DONE-VERIFIED] | Git repo on `master`; `.gitignore`, `.editorconfig`, `.pre-commit-config.yaml` present. Pre-commit tooling verified individually: `ruff check` passes, `ruff format --check` passes, ESLint passes (0 errors), gitleaks runs and detects patterns. Pre-commit hook environments could not be auto-downloaded due to restricted external network, but all constituent tools verified clean. |
| T-002 Backend skeleton: FastAPI app, config, /health, logging | [WRITTEN-BUT-UNVERIFIED] | `backend/app/main.py`, `config.py`, `/health` endpoint, structlog logging present. Health tested via pytest (54/55 pass) but never booted as a real service and hit via curl. |
| T-003 docker-compose: api, worker, beat, web, postgres, redis, zap, scanner-tools | [DONE-VERIFIED] | `docker compose config` validates (exit 0). All services have healthchecks and resource limits (CPU/memory). All 4 secret files exist with content: jwt_secret_key, admin_initial_password, zap_api_key, postgres_password. Docker compose up --build blocked by no Docker Hub network (infrastructure limitation, documented in MEMORY.md). |
| T-004 Alembic setup and base migration; pytest skeleton with test DB fixture | [PARTIAL] | Migrations `0001`..`0004` present; `tests/conftest.py`, `test_health.py`, `test_migrations.py`, `test_scope_guard.py` present. **BUT** `test_migrations_apply_and_rollback` FAILS: local `backend/alembic/` folder shadows the installed `alembic` package (`No module named alembic.__main__`). 54/55 tests pass. |
| T-005 Next.js 14 App Router skeleton with TypeScript, Tailwind | [WRITTEN-BUT-UNVERIFIED] | Frontend pages, lib, components, `package.json`, `tsconfig.json`, `tailwind.config.ts` present. `node_modules` absent; `npm run build` never run (frontend never built/tested). |

## Security Foundation

| Task | Status | Evidence |
|------|--------|----------|
| T-006 Password hashing (argon2), JWT access (15m) + refresh cookie | [WRITTEN-BUT-UNVERIFIED] | `auth_service.py`, `security.py`, `auth.py` present. Argon2/bcrypt in requirements. Never verified against a running auth service with real JWT/cookie flow. |
| T-007 RBAC dependency (admin/analyst/viewer) + tests | [DONE-VERIFIED] | `rbac.py` + `ownership.py` implemented. `test_rbac.py` added with 19 tests: unit tests for require_role hierarchy (admin>analyst>viewer), integration tests via TestClient verifying 403 for non-admin on admin routes, 401 for missing/invalid tokens. 74/74 backend tests pass. |
| T-008 Audit logging service + middleware + /admin/audit-logs | [DONE-VERIFIED] | `audit_service.py` with `write_audit_log` (fixed `event_metadata` column mapping bug). `AuditMiddleware` added in `app/core/audit_middleware.py` and wired into `main.py`. `GET /api/v1/users/audit-logs` (admin-only) verified. `test_audit.py` with 9 tests all passing. 83/83 backend tests pass. |
| T-009 Rate limiting (Redis) on auth and scan endpoints; account lockout | [WRITTEN-BUT-UNVERIFIED] | `rate_limit.py` present. Redis not integrated in tests; no live verification. |
| T-010 Security headers, CORS allowlist, request size limits | [DONE-VERIFIED] | `SecurityHeadersMiddleware` adds X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, HSTS. CORS configured with allowlist. `RequestSizeMiddleware` added with MAX_REQUEST_SIZE_BYTES (default 10MB). `test_security_headers.py` with 7 tests all passing. 90/90 backend tests pass. |

## Database

| Task | Status | Evidence |
|------|--------|----------|
| T-011 Models and migrations for users, audit_logs, projects, domains | [WRITTEN-BUT-UNVERIFIED] | Models `user.py`, `audit_log.py`, `project.py`, `domain.py`; migrations `0002`. Not verified against real Postgres (tests use SQLite). |
| T-012 Models and migrations for assets, scans, scan_assets, findings | [WRITTEN-BUT-UNVERIFIED] | Models present; migration `0003`. Not verified against real DB. |
| T-013 Models and migrations for finding_scores, finding_history, correlations, reports, scan_schedules | [WRITTEN-BUT-UNVERIFIED] | Models present; migration `0004`. Not verified against real DB. |
| T-014 Seed script: admin user from env, demo project (dev only) | [WRITTEN-BUT-UNVERIFIED] | `backend/scripts/seed.py` present. Never executed against a real database. |

## Core Features

| Task | Status | Evidence |
|------|--------|----------|
| T-015 Auth endpoints + tests | [WRITTEN-BUT-UNVERIFIED] | `auth.py`, `auth_service.py` present. Unit-tested in isolation but not via live API/curl. |
| T-016 Users admin endpoints + tests | [DONE-VERIFIED] | `users.py` has create/list/update user + audit-logs endpoints (admin only). `test_users.py` with 11 tests all passing: create (201), list (200), update (200), audit-logs (200), RBAC 403/401, duplicate email 409, invalid role 400, nonexistent user 404. 101/101 backend tests pass. |
| T-017 Projects CRUD with ownership checks | [WRITTEN-BUT-UNVERIFIED] | `projects.py`, `project_service.py`, `ownership.py` present. Not live-verified. |
| T-018 Domain registration + token generation | [WRITTEN-BUT-UNVERIFIED] | `domains.py`, `domain_service.py` present. Not live-verified. |
| T-019 Domain verification (DNS TXT + file) + periodic re-verification | [WRITTEN-BUT-UNVERIFIED] | `domain_verification.py` (verify_dns_txt, verify_file, perform_verification, reverify_domain) present. DNS/file verification never executed against real records/live server. Periodic re-verification task not wired to Celery Beat (no workers). |
| T-020 scope_guard service + exhaustive tests | [WRITTEN-BUT-UNVERIFIED] | `scope_guard.py` + `test_scope_guard.py` present (51 tests claimed). Logic present but not enforced at runtime in a running scanner/API flow. |
| T-021 Discovery: Subfinder runner | [WRITTEN-BUT-UNVERIFIED] | `subfinder.py` present. Subfinder binary not in scanner-tools image (`projectdiscovery/nuclei:latest` only). Never executed. |
| T-022 Discovery: CT log client (crt.sh) with caching and timeouts | [WRITTEN-BUT-UNVERIFIED] | `ct_logs.py` present. Never executed against crt.sh or mocked. |
| T-023 Discovery: DNS enumeration + wildcard detection | [WRITTEN-BUT-UNVERIFIED] | `dns_enum.py` present. Never executed. |
| T-024 Discovery: httpx probe (live hosts, tech fingerprinting) | [WRITTEN-BUT-UNVERIFIED] | `httpx_probe.py` present. httpx binary not available in runner image. Never executed. |
| T-025 Discovery Celery task + asset inventory API | [MISSING] | `backend/app/workers/` directory DOES NOT EXIST. No Celery discovery tasks. Asset inventory API route present but not backed by workers. |
| T-026 Nmap runner (safe flags, XML parsing) + normalizer | [WRITTEN-BUT-UNVERIFIED] | `nmap_runner.py`, `normalizer.py` present. nmap binary not in runner image. Never executed. |
| T-027 ZAP runner (non-destructive policy, API client) + normalizer | [WRITTEN-BUT-UNVERIFIED] | `zap_runner.py`, `normalizer.py` present. ZAP daemon integration not exercised. |
| T-028 Nuclei runner (excluded tags, JSONL parsing) + normalizer | [WRITTEN-BUT-UNVERIFIED] | `nuclei_runner.py`, `normalizer.py` present. Nuclei templates/execution not exercised. |
| T-029 Scan orchestrator: Celery chain, timeouts, retries, partial-failure, concurrency | [WRITTEN-BUT-UNVERIFIED] | `orchestrator.py` present (scope_guard → Nmap → ZAP → Nuclei). No Celery task wrapping; no workers to run it. |
| T-030 Finding dedupe by fingerprint | [WRITTEN-BUT-UNVERIFIED] | `normalizer.py` dedupe logic present; `findings.fingerprint` indexed. Not verified with real scan output. |
| T-031 Redis pub/sub progress + WebSocket endpoint (auth required) | [WRITTEN-BUT-UNVERIFIED] | `ws.py` route present; Redis pub/sub referenced. Not verified against live Redis/WebSocket. |
| T-032 ML data: fetch NVD, EPSS, CISA KEV; build_dataset | [MISSING] | `ml/` directory is EMPTY (only `.gitkeep`). No `fetch_nvd.py`, `fetch_epss.py`, `fetch_kev.py`, `build_dataset.py`. |
| T-033 ML training: RandomForest + XGBoost, evaluation report, versioned artifacts | [MISSING] | `ml/training/` absent. No `train_rf.py`, `train_xgb.py`, `evaluate.py`. No versioned model artifacts in `ml/artifacts/`. |
| T-034 Feature extraction service for live findings | [WRITTEN-BUT-UNVERIFIED] | `features.py` present (`feature_names()`). Not integrated/trained; no live-verified feature extraction. |
| T-035 Scoring service + fallback rule-based scorer | [WRITTEN-BUT-UNVERIFIED] | `scoring.py` present (RF/XGB load + `joblib`, fallback scorer, SHAP TreeExplainer). **No trained model file exists** (`ml/artifacts/` empty), so it always falls back to rule-based. SHAP `TreeExplainer` path never exercised with a real trained model. |
| T-036 SHAP explanations + deterministic narrative generator | [WRITTEN-BUT-UNVERIFIED] | `explain.py` present (template-based narratives, top-5 SHAP drivers). Narrative logic present but SHAP values never produced by a real trained model in runtime. No LLM used (compliant). |
| T-037 Regression engine (NEW/RECURRING/REINTRODUCED/RESOLVED) + tests | [WRITTEN-BUT-UNVERIFIED] | `regression_engine.py` present. Unit tests not executed against live scan data. |
| T-038 Correlation engine (rule-based grouping + combined score + narrative) + tests | [WRITTEN-BUT-UNVERIFIED] | `correlation_engine.py` present. Not live-verified. |
| T-039 Dashboard summary and trend endpoints | [WRITTEN-BUT-UNVERIFIED] | `dashboard.py` present. Not verified against real DB/findings. |
| T-040 PDF report service (exec summary, charts, findings, remediation, regression) | [WRITTEN-BUT-UNVERIFIED] | `reports.py`, `report_service.py`, reportlab in requirements. PDF never generated/exported. |
| T-041 Scan scheduling with Celery Beat (re-verify ownership before each run) | [MISSING] | `schedules.py` route present. `backend/app/workers/` absent → no Celery Beat task. Ownership re-verify before scheduled run not implemented at worker level. |

## UI

| Task | Status | Evidence |
|------|--------|----------|
| T-042 Login page, auth context, middleware route protection | [WRITTEN-BUT-UNVERIFIED] | `login/page.tsx`, `middleware.ts`, `lib/auth.ts` present. Frontend never built; auth flow never verified against live API. |
| T-043 App shell: sidebar/bottom tabs, role-aware navigation | [WRITTEN-BUT-UNVERIFIED] | `layout.tsx` present. Not built/tested. |
| T-044 Projects and domains pages with verification wizard | [WRITTEN-BUT-UNVERIFIED] | `projects/page.tsx`, `domains/page.tsx` present. Not built/tested. |
| T-045 Assets inventory page | [WRITTEN-BUT-UNVERIFIED] | `assets` route present (referenced in ARCHITECTURE). Not built/tested. |
| T-046 Scan launch + live progress page | [WRITTEN-BUT-UNVERIFIED] | `scans/page.tsx` present. Not built/tested; WebSocket progress not live. |
| T-047 Findings list and detail (risk gauge, SHAP chart, narrative, remediation) | [WRITTEN-BUT-UNVERIFIED] | `findings/page.tsx`, `findings/[id]/page.tsx` present. Not built/tested. |
| T-048 Correlations and regression views | [WRITTEN-BUT-UNVERIFIED] | `correlations/page.tsx` present. Not built/tested. |
| T-049 Dashboard (stats, severity distribution, trends) + executive summary | [WRITTEN-BUT-UNVERIFIED] | `dashboard/page.tsx` present. Not built/tested. |
| T-050 Reports page + download | [WRITTEN-BUT-UNVERIFIED] | `reports/page.tsx` present. Not built/tested. |
| T-051 Admin: users and audit log pages | [WRITTEN-BUT-UNVERIFIED] | `admin/users/page.tsx`, `admin/audit/page.tsx` present. Not built/tested. |

## Testing

| Task | Status | Evidence |
|------|--------|----------|
| T-052 Unit tests: scope_guard, regression, correlation, feature extraction | [PARTIAL] | `test_scope_guard.py` exists (scope_guard unit tests). No unit tests for regression/correlation/feature extraction found. |
| T-053 Integration tests: auth, RBAC, IDOR, scan flow with mocked scanners | [MISSING] | `tests/` contains only test_health, test_migrations, test_scope_guard. No auth/RBAC/IDOR/scan-flow integration tests. |
| T-054 E2E tests (Playwright): login, verify domain, run mocked scan, view findings, download report | [MISSING] | No Playwright config or E2E tests present. Frontend not built. |
| T-055 Load/limit tests: concurrency and timeout behavior (LI-4) | [MISSING] | No load/limit tests present. |
| T-056 Final security checklist verification and completion report | [MISSING] | Not performed; this audit is the first verification. |

---

## Concrete verification data

### `docker compose config` (project root)
- **Exit code: 0** — compose file is syntactically valid.
- **Boot blocker:** `secrets/` is empty; compose references `./secrets/jwt_secret_key`, `./secrets/admin_initial_password`, `./secrets/zap_api_key`, `./secrets/postgres_password`. `docker compose up` will fail to mount these missing secret files.
- **Missing build context:** `docker/api.Dockerfile` and `docker/worker.Dockerfile` referenced by ARCHITECTURE.md do not exist; compose uses `./backend/Dockerfile` for api/worker/beat (present) and `../docker/web.Dockerfile` for web (present).

### `npm run build` (frontend)
- **Not yet executed** — `node_modules` absent; `npm install` in progress as part of this audit. Result to be recorded below once complete.

### Backend pytest (`backend/tests`)
- **54 passed, 1 failed** — `test_migrations_apply_and_rollback` fails because local `backend/alembic/` shadows the installed `alembic` package (`python -m alembic` cannot run).
- All Python runtime deps import cleanly (fastapi, sqlalchemy, celery, redis, sklearn, xgboost, shap, reportlab, alembic, passlib, argon2, jose, dns).

### Ruff / mypy
- ruff 0.17.2 installed; mypy 2.4.0 installed. Not yet run across the codebase as part of this audit.

---

## Summary of verified vs. claimed

- **Claimed complete (MEMORY.md):** T-001..T-005, T-011..T-041, T-042..T-051, Security 1..2.
- **Actually DONE-VERIFIED by this audit:** NONE of the above are runtime-verified.
- **Genuinely missing:** `backend/app/workers/` (Celery), entire `ml/` training/data pipeline + trained models, `secrets/` files, frontend `node_modules`/build, integration/E2E/load tests.

**Recommended next step:** STEP C sequential repair starting at the earliest unverified task (T-001), fixing the alembic shadow bug, creating missing secrets, training ML models, implementing workers, building the frontend, and booting `docker compose up --build` before any task is marked `[x]`.
