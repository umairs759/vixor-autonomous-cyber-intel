# VIXOR — Agent Operating Rules (Windows PowerShell 5.1)

This file is the single source of truth for how autonomous agents operate in this repository. It is enforced strictly. Violations block the presentation deliverable.

## 1. Shell rules (PowerShell 5.1 only)

- **Never use `&&` or `||`.** They are not valid statement separators in PowerShell 5.1.
- Chain commands with `;` and check `$LASTEXITCODE` after every command that can fail.
- **Always quote paths** that contain spaces or em dashes (`—`). Example: `cd "C:\Users\usamah\Desktop\VIXOR — Autonomous"`.
- The project folder name uses an **em dash** (U+2014), not a hyphen. Always quote the path.
- Use `Select-Object -First N` instead of Unix `head`.

## 2. Task execution protocol (atomic, one at a time)

- Execute **exactly ONE task at a time**. No bulk completions, no parallel task implementation.
- Create **exactly ONE git commit per task** once all three passes are clean.
- Commit message format: `feat/fix: T-0XX <short description>` (conventional commit).
- Never mark a task `[x]` in TASKS.md unless it is genuinely verified end-to-end.

## 3. Three-pass verification (every single task)

### Pass 1 — Static checks
Run all applicable linters/type-checkers/builds and require a clean exit code:
- Python backend: `ruff check`, `ruff format --check`, `mypy` (strict), `pytest`
- Frontend: `npm run build`, `npx tsc --noEmit`, `npx eslint`, `npm test`
- CI: `docker compose config` must validate

### Pass 2 — Functional verification
Verify against a real runtime (no stubs, no mock bypasses):
- Backend API via `curl.exe`/`httpx` against the running FastAPI service (`/health`, auth endpoints, RBAC, scan pipeline).
- Real DB entries (Postgres via alembic migrations) and audit-log entries.
- Real scan pipeline dispatch only after domain ownership verification (DNS TXT) and `scope_guard` pass.
- ML scoring via trained RandomForest/XGBoost models with SHAP TreeExplainer outputs (zero LLM scoring dependencies).
- Tests run against internal test targets or local mocks; **never** target external infrastructure.

### Pass 3 — Requirements alignment
Cross-check the implemented behavior against `PRD.md`, `ARCHITECTURE.md`, and `RULES.md`:
- Ownership verification (DNS TXT / `.well-known` file) + re-verification every 7 days.
- `scope_guard` enforced in API layer AND at the start of every scanner task.
- Non-destructive scanners only (Nuclei excludes dos/intrusive/fuzz/bruteforce; ZAP non-destructive policy; Nmap safe options).
- No LLM for risk scoring; narratives are deterministic templates from SHAP values.
- Per-tool timeouts, per-project concurrency capped at 2, container CPU/memory caps.

## 4. Artifact maintenance (update after every task)

- `TASKS.md`: mark `[x]` only for verified tasks.
- `MEMORY.md`: record completion, known issues, and test results.
- `AUDIT.md`: refresh status for every task (T-001 through T-056).

## 5. Secrets & security

- Secrets only via environment variables / Docker secrets (files under `./secrets/`).
- Never log secrets, tokens, or password hashes.
- Never shell-interpolate user input; scanner commands use argument lists with `subprocess` (`shell=False`) and allowlisted flags only.
