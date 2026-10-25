# VIXOR — 6-Pillar Security Checklist

## 1. Authentication & Sessions
[ ] argon2 hashing [ ] 15-min access tokens [ ] refresh rotation + revocation on logout [ ] lockout and rate limit [ ] generic login errors
## 2. Authorization & IDOR
[ ] RBAC on all routes [ ] ownership check on every resource query [ ] tests proving cross-user access returns 404/403
## 3. Hardened Deployment & Audit
[ ] TLS via reverse proxy [ ] security headers (CSP, HSTS, X-Frame-Options, nosniff) [ ] internal-only DB/Redis/ZAP [ ] structured audit logs, append-only [ ] non-root containers with resource limits
## 4. Abuse Prevention
[ ] rate limits per user/IP [ ] scan concurrency caps [ ] ownership verification enforced [ ] scope_guard enforced in API and workers [ ] safe-template-only scanning
## 5. Zero Secrets in Client
[ ] only NEXT_PUBLIC_API_BASE_URL public [ ] gitleaks clean [ ] no secrets in logs or error messages [ ] tokens never in localStorage
## 6. Input Validation & Injection Defense
[ ] Pydantic + Zod on all inputs [ ] hostname regex validation [ ] subprocess shell=False with allowlisted flags [ ] parameterized queries only [ ] output encoding in UI and PDF
