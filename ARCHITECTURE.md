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
