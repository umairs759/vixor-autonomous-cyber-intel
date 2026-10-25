# VIXOR — STRIDE Threat Model

Spoofing: stolen JWT, credential stuffing, fake domain ownership claims. Mitigate: short-lived tokens, refresh rotation, lockout, rate limits, token-based ownership proof with periodic re-verification.
Tampering: modified scan results, tampered ML artifacts, altered audit logs. Mitigate: DB constraints, append-only audit table (no update/delete grants), artifact checksum validation at load.
Repudiation: user denies launching a scan. Mitigate: audit logs for every state change with user, IP, timestamp.
Information Disclosure: IDOR on projects/findings/reports, secrets in client, verbose errors, PDF access by URL guessing. Mitigate: ownership checks, no secrets client-side, generic errors, authenticated report downloads with random IDs.
Denial of Service: scan flooding, huge targets, scanner resource exhaustion. Mitigate: rate limits, concurrency caps, timeouts, container limits, pagination.
Elevation of Privilege: analyst reaching admin routes, command injection via domain names into scanner CLIs. Mitigate: RBAC on every route, strict hostname regex validation, shell=False with allowlisted args.
Platform-specific abuse: using VIXOR to attack third parties. Mitigate: ownership verification, scope_guard (suffix, IP, CDN/shared-host blocks), safe templates only, audit trail.
SSRF: scanner or report features reaching internal services. Mitigate: block private/metadata IPs, scanners in isolated network, egress rules.
