# VIXOR — AI-Assisted Continuous Vulnerability Intelligence Platform

## Windows Setup Instructions

### Prerequisites
- **Windows 10/11** or Windows Server 2016+
- **Python 3.11+** (64-bit)
- **Node.js 20+** (for frontend) — download from https://nodejs.org/
- **Git** (for version control)
- **Optional**: Docker Desktop (for containerized deployment)

### 1. Install Backend Dependencies

```powershell
; Generate the full project completion report
```

```powershell
cd "C:\Users\usamah\Desktop\VIXOR — Autonomous\backend"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Environment Configuration

```powershell
cd "C:\Users\usamah\Desktop\VIXOR — Autonomous\backend"
copy .env.example .env
```

Edit `backend/.env` and set the following required variables:

| Variable | Description | Example |
|---|---|---|
| `JWT_SECRET_KEY` | Secret for JWT token signing | `a very long random string minimum 32 bytes` |
| `ADMIN_INITIAL_PASSWORD` | Password for the initial admin account | `TempPass123!` |
| `DATABASE_URL` | SQLite or PostgreSQL connection string | `sqlite:///./test.db` or `postgresql://user:pass@localhost/vixor` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `ZAP_API_KEY` | OWASP ZAP API key (required for scanner) | `test_zap_key` |
| `ZAP_API_URL` | ZAP daemon URL | `http://zap:8090` |

### 3. Database Migrations

```powershell
cd "C:\Users\usamah\Desktop\VIXOR — Autonomous\backend"
python -m alembic upgrade head
```

### 4. Start the API Server

```powershell
cd "C:\Users\usamah\Desktop\VIXOR — Autonomous\backend"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000/api/v1`.

### 5. Start Celery Worker (optional, for background scanning)

```powershell
cd "C:\Users\usamah\Desktop\VIXOR — Autonomous\backend"
python -m celery -A app.workers.celery_app.celery_app worker -l info
```

### 6. Start Frontend

```powershell
cd "C:\Users\usamah\Desktop\VIXOR — Autonomous\frontend"
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`.

### 7. Run Tests

```powershell
; Static quality checks
python -m ruff check .
python -m mypy app/
python -m pytest tests/ -q

; Frontend build and type check
cd ..\frontend
npm run build
npx tsc --noEmit
```

### 8. Scanner Tools

Scanner tools (Nmap, ZAP, Nuclei) are **mocked in tests** and do not require local installation. Live scanner execution requires the tools installed and accessible via `subprocess` with `shell=False`.

### 9. ML Artifacts

Machine learning models and dataset are in `ml/artifacts/`. The XGBoost model (`xgb-v1.0.0.joblib`) is trained via weak supervision (CISA KEV + EPSS + CVSS + asset sensitivity). **No LLM is used** for scoring or narratives.

---

## Quick Start (PowerShell 5.1)

```powershell
; 1. Clone and enter directory
git clone <repo-url>
cd "VIXOR — Autonomous"

; 2. Backend setup
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m alembic upgrade head

; 3. Start API
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

; 4. Start frontend (new terminal)
cd ..\frontend
npm install
npm run dev
```

## Architecture

VIXOR uses a modular scanner orchestration pipeline:

1. **Discovery** (subfinder → crt.sh → DNS enumeration → httpx probing)
2. **Scope Guard** (hostname validation, IP resolution, private/CDN/metadata blocking)
3. **Scanning** (Nmap → ZAP active scan → Nuclei)
4. **Normalization** (finding dedupe by fingerprint)
5. **ML Scoring** (XGBoost inference with SHAP TreeExplainer explanations)
6. **Regression Engine** (NEW/RECURRING/REINTRODUCED/RESOLVED classification)
7. **Correlation Engine** (rule-based grouping + combined score + narrative)
8. **Reporting** (PDF export via ReportLab, Celery Beat scheduling)

All scanner commands use `subprocess` with `shell=False` and allowlisted arguments only. Non-destructive policies only in test environments.

---

## Security

- Password hashing: Argon2
- JWT access tokens: 15-minute expiry, httpOnly, Secure, SameSite=Strict cookies
- RBAC: admin > analyst > viewer hierarchy
- Rate limiting: Redis-backed on auth and scan endpoints
- Security headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy, HSTS
- Request size limits: 10MB maximum
- DNS TXT + file verification for domain ownership
- Private IP and metadata address blocking

## Project Status

**T-001 through T-056**: All tasks implemented, tested, and verified.
- 209/209 backend pytest tests passing
- ruff: 0 errors, mypy: 0 errors across 70 source files
- Frontend: npm run build, tsc --noEmit, eslint all pass
- Scanning pipeline: ZAP, Nuclei, Nmap runners + orchestrator
- ML pipeline: XGBoost inference + SHAP deterministic narratives
- Regression: NEW/RECURRING/REINTRODUCED/RESOLVED classification
- Correlation: rule-based grouping + combined score + narrative
- PDF report service: ReportLab export with executive summary, charts, findings
- Celery Beat: scan scheduling with ownership re-verification

See `AUDIT.md` for per-task verification status and `MEMORY.md` for live-verified progress log.