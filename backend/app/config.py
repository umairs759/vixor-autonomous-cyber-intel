"""VIXOR application configuration via pydantic-settings.

All settings are sourced from environment variables. Only
NEXT_PUBLIC_API_BASE_URL may be exposed to the browser; every other
value is server-side only.
"""

from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL connection URL (psycopg driver)")
    # Redis / Celery
    REDIS_URL: str = Field(..., description="Redis broker / result backend URL")
    # JWT
    JWT_SECRET_KEY: str = Field(..., min_length=32, description="Secret key for signing JWTs")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, ge=1, description="Access token lifetime in minutes")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, description="Refresh token lifetime in days")
    COOKIE_SECURE: bool = Field(default=True, description="Set Secure flag on refresh cookie")
    # CORS
    CORS_ALLOWED_ORIGINS: str = Field(default="https://localhost:3000", description="Comma-separated allowed origins")
    # Admin seed
    ADMIN_EMAIL: str = Field(default="admin@example.com", description="Initial admin email")
    ADMIN_INITIAL_PASSWORD: str = Field(default="change_me_on_first_login", min_length=8, description="Initial admin password")
    # ZAP
    ZAP_API_KEY: str = Field(default="", description="OWASP ZAP API key")
    ZAP_API_URL: str = Field(default="http://zap:8090", description="ZAP daemon API base URL")
    # Scanner limits
    SCAN_TOOL_TIMEOUT_SECONDS: int = Field(default=1800, ge=30, description="Per-tool scanner timeout in seconds")
    MAX_CONCURRENT_SCANS_PER_PROJECT: int = Field(default=2, ge=1, description="Max concurrent scans per project")
    REVERIFY_INTERVAL_DAYS: int = Field(default=7, ge=1, description="Days between domain re-verification checks")
    ALLOW_PRIVATE_IP_SCANNING: bool = Field(default=False, description="Allow scanning private/RFC1918 IPs (lab mode only)")
    # Frontend
    NEXT_PUBLIC_API_BASE_URL: str = Field(default="https://localhost:8000/api/v1", description="Public API base URL (browser-safe)")

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def _jwt_secret_not_default(cls, v: str) -> str:
        if v in ("generate_with_openssl_rand_hex_64", "change_me", "secret", ""):
            raise ValueError("JWT_SECRET_KEY must not be a default or placeholder value")
        return v

    @field_validator("ZAP_API_KEY")
    @classmethod
    def _zap_key_not_default(cls, v: str) -> str:
        if v and v in ("generate_with_openssl_rand_hex_32", "change_me", ""):
            raise ValueError("ZAP_API_KEY must not be a default or placeholder value")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
