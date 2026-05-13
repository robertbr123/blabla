from typing import Any

import pytest
import sentry_sdk
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
    monkeypatch.setenv("SENTRY_DSN", "https://abc@o0.ingest.sentry.io/0")

    init_calls: list[dict[str, Any]] = []

    def _fake_init(**kwargs: Any) -> None:
        init_calls.append(kwargs)

    monkeypatch.setattr(sentry_sdk, "init", _fake_init)
    monkeypatch.setattr(sentry_sdk, "set_tag", lambda *_a, **_k: None)

    assert mod.init_sentry(component="api") is True
    assert len(init_calls) == 1
    # Confirm the kwargs we care about were forwarded
    assert init_calls[0]["dsn"] == "https://abc@o0.ingest.sentry.io/0"
    assert init_calls[0]["traces_sample_rate"] == 0.0
    assert init_calls[0]["send_default_pii"] is False

    # Second call is idempotent — no additional sentry_sdk.init call
    assert mod.init_sentry(component="api") is False
    assert len(init_calls) == 1


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
    assert out["breadcrumbs"]["values"][1]["message"] == "other"
