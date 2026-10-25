# VIXOR — Attack Surface Inventory

Public endpoints: POST /auth/login, POST /auth/refresh.
Authenticated endpoints: every route listed in ARCHITECTURE.md section 7.
Admin-only: /users, /admin/audit-logs.
WebSocket: /ws/scans/{id} (JWT validated on connect, ownership checked).
User inputs: email/password, project name/description, root domain, verification method, asset selection, scan options, schedule cron expressions, report requests.
High-risk inputs: domain/hostname (command-injection and SSRF vector), cron expression (validate against allowlist presets), uploaded nothing (no file uploads in MVP).
Outbound calls: crt.sh, NVD, EPSS, CISA KEV (fetched by offline ML scripts, not at request time), DNS queries, target HTTP/TCP via scanners.
Auth surfaces: access JWT in Authorization header, refresh token httpOnly cookie, Next.js middleware cookie checks.
Containers: api, worker, beat, web, postgres, redis, zap, scanner-tools. Only web and api exposed through the reverse proxy; postgres, redis, zap internal only.
File system: report PDFs and ML artifacts (not publicly served).
