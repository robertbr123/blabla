"""Tests for the Settings configuration class."""
from __future__ import annotations

from pathlib import Path

import pytest
from ondeline_api.config import Settings
from pydantic import ValidationError


def test_settings_loads_from_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://u:p@localhost:5432/db",
    )
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    settings = Settings()

    assert settings.env == "development"
    assert settings.log_level == "DEBUG"
    assert str(settings.database_url) == "postgresql+asyncpg://u:p@localhost:5432/db"
    assert str(settings.redis_url) == "redis://localhost:6379/0"


def test_settings_defaults_when_optional_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    # Required vars set; optional ones absent
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db"
    )
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.delenv("EVOLUTION_KEY", raising=False)

    settings = Settings()

    assert settings.env == "development"  # default
    assert settings.evolution_key == ""  # default empty


def test_settings_fails_when_required_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings()


def _base_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/d")
    monkeypatch.setenv("REDIS_URL", "redis://h:6379/0")
    # Garante que .env real do projeto nao vaze pro teste
    for k in (
        "LLM_PROVIDER", "OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_URL",
        "XAI_API_KEY", "XAI_MODEL", "XAI_URL",
        "HERMES_API_KEY", "HERMES_MODEL", "HERMES_URL",
    ):
        monkeypatch.delenv(k, raising=False)


def test_effective_llm_defaults_to_openai(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    url, key, model = Settings().effective_llm()
    assert url == "https://api.openai.com/v1"
    assert key == "sk-test"
    assert model == "gpt-4o-mini"


def test_effective_llm_xai_when_provider_grok(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("LLM_PROVIDER", "grok")
    monkeypatch.setenv("XAI_API_KEY", "xai-test")
    monkeypatch.setenv("XAI_MODEL", "grok-2")

    url, key, model = Settings().effective_llm()
    assert url == "https://api.x.ai/v1"
    assert key == "xai-test"
    assert model == "grok-2"


def test_effective_llm_hermes_legacy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("LLM_PROVIDER", "hermes")
    monkeypatch.setenv("HERMES_URL", "http://10.0.0.5:8642/v1")
    monkeypatch.setenv("HERMES_API_KEY", "local-key")
    monkeypatch.setenv("HERMES_MODEL", "Hermes-3")

    url, key, model = Settings().effective_llm()
    assert url == "http://10.0.0.5:8642/v1"
    assert key == "local-key"
    assert model == "Hermes-3"


def test_effective_llm_openai_falls_back_to_hermes_key_for_migration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Quando OPENAI_API_KEY esta vazio mas HERMES_API_KEY tem a chave do
    OpenAI (cenario de migracao), usa HERMES_API_KEY."""
    _base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("HERMES_API_KEY", "sk-legacy")

    url, key, _model = Settings().effective_llm()
    assert url == "https://api.openai.com/v1"
    assert key == "sk-legacy"
