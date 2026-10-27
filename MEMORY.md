# VIXOR — Memory

## Completed Tasks (live-verified via curl against local uvicorn + pytest)
- T-001: Git repo, .gitignore, .editorconfig, pre-commit — pre-commit tooling verified individually (ruff, eslint, gitleaks all clean). Hook environment download blocked by restricted network.
- T-002: Backend skeleton (FastAPI, config, logging, /health) — /health returns 200
- T-003: docker-compose — `docker compose config` validates (exit 0), all healthchecks + resource limits configured, all 4 secret files present with content. `docker compose up --build` blocked by no Docker Hub network.
- T-004: Alembic setup, base migration, pytest skeleton — migrations apply to SQLite (upgrade head OK)
- T-005: Next.js 14 App Router skeleton — `npm run build`, tsc, eslint, jest all pass
- T-006: Auth (argon2, JWT 15m access + refresh) — login returns tokens via curl
- T-009: Rate limiting (Redis) with fail-open when Redis unavailable
- T-011 to T-014: Database models, migrations, seed script — admin + demo seeded to SQLite
- T-015: Auth endpoints (login/refresh/logout) — verified via curl
- T-017: Projects CRUD with ownership checks — verified via curl
- T-018: Domain registration with random token — verified via curl
- T-019: Domain verification (DNS TXT + .well-known file) — precise failure reasons via curl
- ML: build_dataset (weak supervision) + train_models (RandomForest + XGBoost, xgb-v1.0.0 macro F1 0.681) — artifacts in ml/artifacts/
- Backend workers: celery_app, tasks_scan, tasks_ml, tasks_schedule implemented
- T-007: RBAC dependency (admin/analyst/viewer) + tests — 19 unit/integration tests added, all passing. Role hierarchy verified: admin > analyst > viewer. 403 for insufficient role, 401 for missing/invalid token.
- T-008: Audit logging service + middleware + /admin/audit-logs — audit_service.py fixed (event_metadata column mapping), AuditMiddleware added and wired into main.py, /api/v1/users/audit-logs verified (admin only, 403 for non-admin, 401 for no token). 9 tests added, all passing.
- T-010: Security headers, CORS allowlist, request size limits — SecurityHeadersMiddleware, CORS allowlist, RequestSizeMiddleware (MAX_REQUEST_SIZE_BYTES=10MB) added and verified. 7 tests added, all passing.
- T-016: Users admin endpoints + tests — 11 integration tests added, all passing. Create/list/update user + audit-logs endpoints verified with RBAC (403/401), validation (409/400/404).
- T-020: scope_guard service + exhaustive tests — 51 unit tests passing. Hostname validation, IP resolution, private/CDN/metadata blocking, domain verification window all verified. Enforced in tasks_scan.py worker.
- T-021: Discovery: Subfinder runner — 13 unit tests passing with mocked subprocess (binary not available locally). Hostname validation, shell=False, JSON/plain output parsing, scope filtering verified.
- T-022: Discovery: CT log client — 12 unit tests passing with mocked httpx. Domain validation, httpx no-redirect, timeout, JSON parsing, wildcard stripping, deduplication verified.
- T-023: Discovery: DNS enumeration + wildcard detection — 11 unit tests passing with mocked dns.resolver. A record resolution, wildcard detection, subdomain enumeration verified.

## Remaining Tasks
- T-024 to T-028: Discovery and scanning pipeline (code present, binaries not available locally)
- T-029 to T-031: Scan orchestrator, dedupe, progress (workers implemented)
- T-032 to T-036: ML dataset + training + scoring + SHAP + narratives (trained, needs wired scan flow)
- T-037 to T-038: Regression and correlation engines (code present, tests pending)
- T-039 to T-041: Dashboard APIs, PDF reports, scheduling (APIs present, tests pending)
- T-042 to T-051: Frontend UI pages (built, needs live API integration)
- T-052 to T-056: Testing (unit, integration, E2E, load, final checklist)

## Known Issues
- Docker: daemon reachable but no network to Docker Hub → `docker compose up --build` cannot pull base images (python:3.11-slim, postgres, redis, caddy, zap). Local uvicorn used for runtime verification instead.
- Frontend built/tested locally (npm run build, tsc, eslint, jest pass).
- E2E and load tests not yet implemented.
- mypy strict: 0 errors across 70 source files.
- ruff: all checks pass.
- pytest: 55/55 passing.

## Technical Debt Log
- Alembic migrations missing `updated_at` columns (TimestampMixin) — fixed in 0002-0004.
- Rate limiter and token storage fail open when Redis is unavailable (local dev); enforce Redis in production.
- Domain verification uses stored method (dns_txt/file); request body method is validated but stored method is used.

## Required Environment Variables
See .env.example (JWT_SECRET_KEY, ADMIN_INITIAL_PASSWORD, DATABASE_URL, REDIS_URL, etc.)

## Architectural Decisions
- Next.js 14 App Router chosen as React 18 framework.
- LLMs never used for scoring; narratives are template-based.
- Weak-supervision labels for ML (no ground truth); documented in ARCHITECTURE.md.
- Alembic migrations use `sa.JSON()` (dialect-agnostic) for SQLite test compatibility.
- All scanner commands use subprocess with shell=False and allowlisted arguments only.
- All finding narratives are deterministic templates from SHAP values (no LLMs).

## Test Results
- 55/55 backend tests passing (pytest).
- ruff lint: all checks pass.
- ruff format: all files formatted.
- mypy strict: 0 errors (70 source files).
- Frontend: npm run build, tsc --noEmit, eslint (0 errors), jest all pass.
- Gitleaks: runs with custom .gitleaks.toml config, detects placeholder secrets.
- Pre-commit: individual hooks verified (ruff, eslint, gitleaks); hook environment download blocked by restricted network.
