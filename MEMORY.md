# VIXOR — Memory

## Completed Tasks
- T-001: Git repo, .gitignore, .editorconfig, pre-commit
- T-002: Backend skeleton (FastAPI, config, logging, /health)
- T-003: docker-compose with all services
- T-004: Alembic setup, base migration, pytest skeleton
- T-005: Next.js 14 App Router skeleton
- T-011 to T-014: Database models, migrations, seed script
- T-015: Auth endpoints (login, refresh, logout)
- T-016: Users admin endpoints + audit-logs
- T-017: Projects CRUD with ownership checks
- T-018: Domain registration with random token
- T-019: Domain verification (DNS TXT + .well-known file)
- T-020: scope_guard service + 51 unit tests
- Security 1: Refresh token rotation, reuse detection, per-IP rate limiting
- Security 2: IDOR prevention & row-level data ownership pattern
- T-021 to T-028: Discovery and scanning pipeline (subfinder, ct_logs, dns_enum, httpx, nmap, zap, nuclei, normalizer, orchestrator)
- T-029 to T-031: Scan orchestrator, dedupe, progress (partially)
- T-032 to T-036: ML dataset, training, scoring, SHAP, narratives
- T-037 to T-038: Regression and correlation engines
- T-039 to T-041: Dashboard APIs, PDF reports, scheduling (APIs created)
- T-042 to T-051: Frontend UI pages (projects, domains, scans, findings, correlations, reports, admin users/audit)

## Remaining Tasks
- T-052: Unit tests (regression, correlation, feature extraction)
- T-053: Integration tests (auth, RBAC, IDOR, scan flow)
- T-054: E2E tests (Playwright)
- T-055: Load/limit tests
- T-056: Final security checklist verification and completion report
- Security 3: Hardened deployment, TLS, audit logging
- Security 4: Abuse prevention, rate limiting
- Security 5: Zero secrets in client
- Security 6: Input sanitization, Zod validation

## Known Issues
- mypy package installed is v2.4.0 (unexpected version); strict mypy check not yet run.
- Frontend not yet built/tested (Node.js not installed in environment).
- Docker not available for container testing.
- E2E and load tests not yet implemented.

## Technical Debt Log
- None yet.

## Required Environment Variables
See security/secrets.md

## Architectural Decisions
- Next.js 14 App Router chosen as React 18 framework.
- LLMs never used for scoring; narratives are template-based.
- Weak-supervision labels for ML (no ground truth); documented in ARCHITECTURE.md.
- Stage 1: PRD validated; added Limitations section (LI-1 to LI-4) and US-12 (dashboard).
- Stage 2: Stack verified (FastAPI 0.115, SQLAlchemy 2.0.36, PostgreSQL 15, Redis 7, Celery 5.4, Next.js 14.2.15, Node 20, scikit-learn 1.5.2, XGBoost 2.1.1, SHAP 0.46.0); all Docker-compatible.
- Stage 3: Architecture sign-off — scope_guard enforced in API and workers; non-destructive scanner settings; no LLMs in scoring path.
- AuditLog column renamed from `metadata` to `event_metadata` (SQLAlchemy reserves `metadata`).
- Alembic migrations use `sa.JSON()` instead of `postgresql.JSONB(as_text_type=...)` for SQLite test compatibility.
- All scanner commands use subprocess with shell=False and allowlisted arguments only.
- All finding narratives are deterministic templates from SHAP values (no LLMs).

## Test Results
- 55/55 backend tests passing (pytest).
- ruff lint: all checks pass.
- ruff format: all files formatted.
