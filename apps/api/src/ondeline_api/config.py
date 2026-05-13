"""Application settings loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
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
        description="psycopg sync URL (reserved for future tooling, not used by Alembic)",
    )

    # Redis (str preserves the value exactly as provided)
    redis_url: str = Field(..., description="redis://host:port/db")

    # Evolution API
    evolution_url: str = "http://localhost:8080"
    evolution_key: str = ""
    evolution_hmac_secret: str = ""
    evolution_instance: str = "hermes-wa"
    evolution_ip_allowlist: str = ""  # CSV; vazio = sem allowlist

    # Webhook
    webhook_max_body_bytes: int = 1_048_576  # 1 MB
    webhook_rate_limit: str = "100/minute"

    # Bot
    bot_ack_text: str = (
        "Olá! 😊 Recebi sua mensagem. "
        "Em instantes um de nossos atendentes vai falar com você."
    )

    # Celery
    celery_broker_url: str = ""  # default: usa redis_url
    celery_result_backend: str = ""  # default: usa redis_url

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
    hermes_model: str = "Hermes-3"

    # LLM controls
    llm_max_iter: int = 5
    llm_timeout_seconds: float = 30.0
    llm_max_tokens_per_conversa_dia: int = 50_000
    llm_history_turns: int = 12  # ultimas N mensagens incluidas no prompt

    # SGP cache TTL (segundos)
    sgp_cache_ttl_cliente: int = 3600
    sgp_cache_ttl_faturas: int = 300
    sgp_cache_ttl_negativo: int = 300

    # Auth
    jwt_secret: SecretStr = SecretStr("")
    pii_encryption_key: SecretStr = SecretStr("")
    pii_hash_pepper: SecretStr = SecretStr("")

    # Timing oracle mitigation: pre-computed argon2id hash for nonexistent users.
    # If empty at startup, auth module computes one lazily (cheaper than re-hashing per request).
    dummy_password_hash: str = ""

    # Token TTLs
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7

    # Cookies
    cookie_secure: bool = True
    cookie_domain: str = ""
    cookie_samesite: str = "strict"

    # Observabilidade
    sentry_dsn: str = ""

    # Tracing (OpenTelemetry)
    otel_exporter_otlp_endpoint: str = ""  # ex: http://tempo:4318
    otel_service_name: str = "ondeline-api"

    def effective_celery_broker(self) -> str:
        return self.celery_broker_url or self.redis_url

    def effective_celery_result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    def evolution_ip_allowlist_set(self) -> set[str]:
        return {ip.strip() for ip in self.evolution_ip_allowlist.split(",") if ip.strip()}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Construct and cache a Settings instance from current environment.

    Use get_settings.cache_clear() in tests to force re-reading env vars.
    """
    return Settings()
