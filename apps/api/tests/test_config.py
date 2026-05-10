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
