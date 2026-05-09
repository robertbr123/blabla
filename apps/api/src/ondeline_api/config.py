"""Application settings loaded from environment variables."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized settings. Read once at startup, then immutable."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Aplicação
    env: str = "development"
    log_level: str = "INFO"

    # Banco
    database_url: str = Field(..., description="postgresql+asyncpg://...")
    database_url_sync: str = Field(
        default="",
        description="psycopg sync URL (Alembic + tools)",
    )

    # Redis (str preserves the value exactly as provided)
    redis_url: str = Field(..., description="redis://host:port/db")

    # Evolution API (preenchido em milestones futuros)
    evolution_url: str = "http://localhost:8080"
    evolution_key: str = ""
    evolution_hmac_secret: str = ""

    # SGP
    sgp_ondeline_base: str = "https://ondeline.sgp.tsmx.com.br"
    sgp_ondeline_token: str = ""
    sgp_ondeline_app: str = "mikrotik"
    sgp_linknetam_base: str = "https://linknetam.sgp.net.br"
    sgp_linknetam_token: str = ""
    sgp_linknetam_app: str = "APP"

    # Hermes LLM
    hermes_url: str = "http://127.0.0.1:8642/v1"
    hermes_api_key: str = ""
    hermes_model: str = "anthropic/claude-opus-4.6"

    # Auth
    jwt_secret: str = ""
    pii_encryption_key: str = ""
    pii_hash_pepper: str = ""

    # Observabilidade
    sentry_dsn: str = ""


def get_settings() -> Settings:
    """Construct a Settings instance from current environment.

    Wrapped with lru_cache in deps.py for singleton behavior at runtime.
    """
    return Settings()
