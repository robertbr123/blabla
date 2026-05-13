import pytest
from ondeline_api.config import get_settings
from ondeline_api.services import sentry_init as mod


def _reset() -> None:
    mod._INITIALIZED = False
    get_settings.cache_clear()


def test_init_sentry_noop_when_dsn_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset()
    monkeypatch.setenv("SENTRY_DSN", "")
    assert mod.init_sentry(component="api") is False


def test_init_sentry_runs_when_dsn_set(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset()
    # Sentry accepts any valid-looking DSN even offline.
    monkeypatch.setenv("SENTRY_DSN", "https://abc@o0.ingest.sentry.io/0")
    assert mod.init_sentry(component="api") is True
    # Second call is idempotent — returns False
    assert mod.init_sentry(component="api") is False


def test_before_send_masks_pii_in_message() -> None:
    event = {
        "message": "user joao@example.com com CPF 123.456.789-00",
        "breadcrumbs": {"values": [
            {"message": "fetched 987.654.321-00"},
            {"message": "other"},
        ]},
    }
    out = mod._before_send(event, {})
    assert out is not None
    assert "[EMAIL]" in out["message"]
    assert "[CPF]" in out["message"]
    assert out["breadcrumbs"]["values"][0]["message"] == "fetched [CPF]"
