# VIXOR — Product Requirements Document

## 1. Problem
Security teams drown in raw, isolated scanner alerts. Static CVSS ignores asset sensitivity, exploit availability, auth barriers, and recurrence. Scanners give no explanation for severity, and every scan is independent, so teams cannot tell whether a vulnerability is new, recurring, or reintroduced. Commercial platforms are expensive.

## 2. Target Users
- Security Analyst: runs scans, triages findings, reads explanations.
- Administrator: manages users, roles, projects, audit logs.
- Management stakeholder (read-only): views executive summary and PDF reports.

## 3. Core Features (map to objectives)
- BO-1 Attack surface discovery: Subfinder + Certificate Transparency logs, DNS enumeration, live host detection, technology fingerprinting, asset inventory.
- BO-2 Unified scanning pipeline: Nuclei, OWASP ZAP, Nmap.
- BO-3 Contextual ML risk scoring (RandomForest + XGBoost).
- BO-4 Explainability: SHAP values + natural-language risk narratives.
- BO-5 Security correlation engine: groups related findings into attack narratives.
- BO-6 Regression intelligence: classifies each finding per scan cycle as NEW, RECURRING, REINTRODUCED, or RESOLVED.
- BO-7 Dashboard with real-time progress and visual analytics.
- BO-8 Professional PDF reports with risk summary and remediation guidance.
- BO-9 JWT auth, RBAC, audit logging.
- BO-10 Ethical scanning policy: ownership verification, scope enforcement, safe templates only.
- Scan scheduling (Celery Beat) and security posture trend tracking.

## 4. MVP Scope
IN: everything above for web apps, APIs, and subdomain infrastructure.
OUT: exploit execution, destructive pentesting, unauthorized targets, mobile apps, network-internal (non-internet-facing) scanning, multi-tenant billing.

## 5. User Stories & Acceptance Criteria
US-01 As an Analyst, I log in and receive a 15-min access token and a refresh cookie.
  AC: wrong password returns generic error; 5 failures in 10 min locks the account for 15 min; audit log entry written.
US-02 As an Admin, I create users and assign roles.
  AC: only Admin can hit /admin/*; Analyst gets 403; change is audit-logged.
US-03 As an Analyst, I create a project and register a domain.
  AC: domain starts as UNVERIFIED with a random token; scans are blocked until verified.
US-04 As an Analyst, I verify ownership via DNS TXT record (_vixor-verify.<domain>) or a file at /.well-known/vixor-verification.txt.
  AC: verification checks the exact token; success sets verified_at; failure gives a precise reason.
US-05 As an Analyst, I run discovery on a verified domain.
  AC: only subdomains ending in the verified root are stored; each asset has resolved IPs, live status, and detected technologies.
US-06 As an Analyst, I start a scan on selected assets.
  AC: scan rejected if asset out of scope or domain unverified; progress streams live; per-tool timeouts enforced.
US-07 As an Analyst, I view scored findings with an explanation.
  AC: each finding shows risk score 0-100, top 5 SHAP drivers, and a narrative sentence.
US-08 As an Analyst, I see regression status between scans.
  AC: finding fingerprint matched across scans; status is correct for NEW/RECURRING/REINTRODUCED/RESOLVED.
US-09 As an Analyst, I see correlated attack narratives.
  AC: e.g., exposed admin panel + outdated component + missing auth header are grouped with a combined narrative and combined risk.
US-10 As an Analyst/Management user, I download a PDF report.
  AC: includes executive summary, risk distribution, top findings with explanations, remediation guidance, regression trends.
US-11 As an Analyst, I schedule recurring scans (daily/weekly).
  AC: schedule persists; Celery Beat triggers; ownership re-verified before each scheduled run.

## 6. Edge Cases
- Domain token removed after verification: re-verification every 7 days; failure suspends scanning.
- Wildcard DNS returns IPs for any subdomain: detect and dedupe.
- Subdomain resolves to third-party/CDN/shared-hosting IP: flagged OUT_OF_SCOPE, never scanned.
- Scanner timeout or container crash: scan marked PARTIAL with reasons; other tools' results kept.
- Duplicate findings from multiple tools: deduplicated by fingerprint.
- ML model missing: scan completes with fallback rule-based score flagged "unscored by ML".
- Concurrent scans on same asset: queued, not parallel.
- Very large result sets: paginated APIs, streamed PDF generation.
