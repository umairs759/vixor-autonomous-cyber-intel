# VIXOR — Secrets & Environment Variables

.env.example:
DATABASE_URL=postgresql+psycopg://vixor:change_me@postgres:5432/vixor
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=generate_with_openssl_rand_hex_64
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
COOKIE_SECURE=true
CORS_ALLOWED_ORIGINS=https://localhost:3000
ADMIN_EMAIL=admin@example.com
ADMIN_INITIAL_PASSWORD=change_me_on_first_login
ZAP_API_KEY=generate_with_openssl_rand_hex_32
ZAP_API_URL=http://zap:8090
SCAN_TOOL_TIMEOUT_SECONDS=1800
MAX_CONCURRENT_SCANS_PER_PROJECT=2
REVERIFY_INTERVAL_DAYS=7
ALLOW_PRIVATE_IP_SCANNING=false
NEXT_PUBLIC_API_BASE_URL=https://localhost:8000/api/v1

Rules: only NEXT_PUBLIC_API_BASE_URL may be exposed to the browser. Rotate JWT_SECRET_KEY and ZAP_API_KEY every 90 days or on suspected leak; rotating JWT key invalidates sessions. Never commit .env. gitleaks runs in pre-commit and CI.
