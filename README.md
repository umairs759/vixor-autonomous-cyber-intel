# VIXOR - AI-Assisted Continuous Vulnerability Intelligence Platform

## Windows Setup

1. Install Python 3.11+, Node.js 20+, and (optional) Docker Desktop.
2. Clone the repository and enter the project directory.
3. Create a virtual environment and install backend dependencies:
   ```powershell
   cd backend
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `backend/.env` and set `JWT_SECRET_KEY`, `ADMIN_INITIAL_PASSWORD`, `DATABASE_URL`, `REDIS_URL`.
5. Run database migrations:
   ```powershell
   cd backend
   python -m alembic upgrade head
   ```
6. Start the API:
   ```powershell
   cd backend
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
7. Start the Celery worker (optional):
   ```powershell
   cd backend
   python -m celery -A app.workers.celery_app.celery_app worker -l info
   ```
8. Frontend:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```
9. Run tests:
   ```powershell
   cd backend
   python -m ruff check .
   python -m mypy app/
   python -m pytest tests/ -q
   cd ..\frontend
   npm run build
   npx tsc --noEmit
   ```

## Notes
- Scanner tools (Nmap, ZAP, Nuclei) are mocked in tests; live runs require the tools installed.
- ML artifacts are in `ml/artifacts/` (XGBoost v1.0.0). No LLM is used for scoring.
PY