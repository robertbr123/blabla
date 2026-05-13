"""Tests for the global structlog configuration with PII masking."""
from __future__ import annotations

import json
import logging

import pytest
import structlog
from ondeline_api.config import get_settings
from ondeline_api.services.logging_config import (
    _mask_pii_processor,
    _walk,
    configure_logging,
)


def _reset_structlog() -> None:
    structlog.reset_defaults()
    import ondeline_api.services.logging_config as mod

    mod._CONFIGURED = False


def test_mask_pii_walk_masks_cpf_in_nested_dict() -> None:
    out = _walk({"a": "cliente 123.456.789-00 ativo", "b": {"c": ["111.222.333-44"]}})
    assert "[CPF]" in out["a"]
    assert out["b"]["c"] == ["[CPF]"]


def test_mask_pii_walk_masks_email_in_list() -> None:
    out = _walk(["manda pra a@b.com agora"])
    assert "[EMAIL]" in out[0]


def test_mask_pii_walk_masks_tuple_recursively() -> None:
    out = _walk(("a@b.com", "ola"))
    assert isinstance(out, tuple)
    assert "[EMAIL]" in out[0]
    assert out[1] == "ola"


def test_mask_pii_walk_preserves_non_strings() -> None:
    assert _walk(42) == 42
    assert _walk(None) is None
    assert _walk(True) is True
    assert _walk(3.14) == 3.14


def test_mask_pii_processor_masks_event_dict() -> None:
    out = _mask_pii_processor(None, "info", {"email": "a@b.com", "n": 1})
    assert out["email"] == "[EMAIL]"
    assert out["n"] == 1


def test_configure_logging_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_structlog()
    get_settings.cache_clear()
    try:
        configure_logging()
        # second call must be a no-op (no exception, no reconfiguration loop)
        configure_logging()
    finally:
        _reset_structlog()
        get_settings.cache_clear()


def test_mask_pii_in_json_renderer_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _reset_structlog()
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    get_settings.cache_clear()
    try:
        configure_logging()
        log = structlog.get_logger("test")
        log.info("event", email="joao@example.com", cpf_str="123.456.789-00")
        captured = capsys.readouterr().out
        lines = [ln for ln in captured.splitlines() if "event" in ln]
        assert lines, f"expected an 'event' line in stdout, got: {captured!r}"
        payload = json.loads(lines[-1])
        assert payload["email"] == "[EMAIL]"
        assert payload["cpf_str"] == "[CPF]"
        assert payload["event"] == "event"
    finally:
        _reset_structlog()
        get_settings.cache_clear()
        logging.getLogger().handlers.clear()


def test_mask_pii_masks_nested_dict_value_in_json_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _reset_structlog()
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    get_settings.cache_clear()
    try:
        configure_logging()
        log = structlog.get_logger("test")
        log.info("nested", payload={"cpf": "111.222.333-44"})
        captured = capsys.readouterr().out
        lines = [ln for ln in captured.splitlines() if "nested" in ln]
        assert lines
        payload = json.loads(lines[-1])
        assert payload["payload"] == {"cpf": "[CPF]"}
    finally:
        _reset_structlog()
        get_settings.cache_clear()
        logging.getLogger().handlers.clear()


def test_console_renderer_used_in_development(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _reset_structlog()
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    get_settings.cache_clear()
    try:
        configure_logging()
        log = structlog.get_logger("test")
        log.info("hello", email="x@y.com")
        captured = capsys.readouterr().out
        # Console output is not valid JSON (so the production assertion would fail here)
        assert "hello" in captured
        # Verify PII masking still happens in dev
        assert "[EMAIL]" in captured
        assert "x@y.com" not in captured
    finally:
        _reset_structlog()
        get_settings.cache_clear()
        logging.getLogger().handlers.clear()
