import pytest
from ondeline_api.config import get_settings
from ondeline_api.services import otel_init as mod


def _reset() -> None:
    mod._INITIALIZED = False
    get_settings.cache_clear()


def test_init_otel_noop_when_endpoint_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset()
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    assert mod.init_otel(component="api") is False


def test_init_otel_runs_when_endpoint_set(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset()
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    assert mod.init_otel(component="worker") is True
    # Idempotent — second call no-op
    assert mod.init_otel(component="worker") is False
