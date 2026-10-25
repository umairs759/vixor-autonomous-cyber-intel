# VIXOR — Memory

## Active State
Current task: T-015
Last completed: T-014

## Required Environment Variables
See security/secrets.md

## Architectural Decisions
- Next.js 14 App Router chosen as React 18 framework.
- LLMs never used for scoring; narratives are template-based.
- Weak-supervision labels for ML (no ground truth); documented in ARCHITECTURE.md.
- Stage 1: PRD validated; added Limitations section (LI-1 to LI-4) and US-12 (dashboard).
- Stage 2: Stack verified (FastAPI 0.115, SQLAlchemy 2.0.36, PostgreSQL 15, Redis 7, Celery 5.4, Next.js 14.2.15, Node 20, scikit-learn 1.5.2, XGBoost 2.1.1, SHAP 0.46.0); all Docker-compatible.
- Stage 3: Architecture sign-off — scope_guard enforced in API and workers; non-destructive scanner settings; no LLMs in scoring path.

## Known Issues

## Technical Debt Log
