"""
app/core/config.py
==================
Centralised application settings loaded from environment variables via Pydantic-Settings.
All values are validated at startup — no silent misconfiguration.
"""

from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME: str = "AI-Native ERP"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = False

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ------------------------------------------------------------------
    # Supabase
    # ------------------------------------------------------------------
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # ------------------------------------------------------------------
    # Database (direct Postgres connection for SQLAlchemy async)
    # ------------------------------------------------------------------
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@host:5432/db

    # ------------------------------------------------------------------
    # Connection Pool Tuning (asyncpg / SQLAlchemy)
    # ------------------------------------------------------------------
    DB_POOL_SIZE: int = 10        # persistent connections per worker process
    DB_MAX_OVERFLOW: int = 20     # extra burst connections beyond pool_size
    DB_POOL_TIMEOUT: int = 30     # seconds to wait for a free connection
    DB_POOL_RECYCLE: int = 1800   # seconds before a connection is recycled

    # ------------------------------------------------------------------
    # CORS / Hosts
    # ------------------------------------------------------------------
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]

    # ------------------------------------------------------------------
    # AI / LLM Keys
    # ------------------------------------------------------------------
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # ------------------------------------------------------------------
    # Redis / Celery
    # ------------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"

    # ------------------------------------------------------------------
    # Sentry
    # ------------------------------------------------------------------
    SENTRY_DSN: str = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()


settings = get_settings()
