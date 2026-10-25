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
