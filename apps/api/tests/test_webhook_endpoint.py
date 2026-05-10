"""Endpoint POST /webhook — HMAC, body limit, rate limit, IP allowlist."""
from __future__ import annotations

import hashlib
import hmac as _hmac
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

SECRET = "test-secret-9001"


def _sign(body: bytes) -> str:
    return f"sha256={_hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()}"


PAYLOAD = {
    "event": "messages.upsert",
    "data": {
        "key": {"id": "WAEVT_E2E_1", "remoteJid": "5511@s.whatsapp.net", "fromMe": False},
        "pushName": "X",
        "message": {"conversation": "Oi"},
    },
}


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setenv("EVOLUTION_HMAC_SECRET", SECRET)
    monkeypatch.setenv("WEBHOOK_RATE_LIMIT", "1000/minute")
    monkeypatch.setenv("WEBHOOK_MAX_BODY_BYTES", "2048")
    from ondeline_api.config import get_settings

    get_settings.cache_clear()

    # Intercepta a delay() pra nao precisar broker real
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "ondeline_api.api.webhook.process_inbound_message_task.delay",
        lambda payload: captured.append(payload),
    )

    from ondeline_api.main import create_app

    app = create_app()
    c = TestClient(app)
    c.captured = captured  # type: ignore[attr-defined]
    return c


def test_valid_signature_returns_202(client: TestClient) -> None:
    body = json.dumps(PAYLOAD).encode()
    r = client.post("/webhook", content=body, headers={"X-Hub-Signature-256": _sign(body)})
    assert r.status_code == 202
    assert r.json()["status"] == "accepted"


def test_missing_signature_returns_401(client: TestClient) -> None:
    body = json.dumps(PAYLOAD).encode()
    r = client.post("/webhook", content=body)
    assert r.status_code == 401


def test_bad_signature_returns_401(client: TestClient) -> None:
    body = json.dumps(PAYLOAD).encode()
    r = client.post(
        "/webhook", content=body, headers={"X-Hub-Signature-256": "sha256=deadbeef"}
    )
    assert r.status_code == 401


def test_oversized_body_returns_413(client: TestClient) -> None:
    big = json.dumps({"event": "messages.upsert", "data": {"x": "y" * 4096}}).encode()
    r = client.post(
        "/webhook", content=big, headers={"X-Hub-Signature-256": _sign(big)}
    )
    assert r.status_code == 413


def test_invalid_json_returns_400(client: TestClient) -> None:
    body = b"not json"
    r = client.post(
        "/webhook", content=body, headers={"X-Hub-Signature-256": _sign(body)}
    )
    assert r.status_code == 400


def test_non_messages_event_returns_200_ignored(client: TestClient) -> None:
    body = json.dumps({"event": "presence.update", "data": {}}).encode()
    r = client.post(
        "/webhook", content=body, headers={"X-Hub-Signature-256": _sign(body)}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"


def test_ip_allowlist_blocks_unknown(monkeypatch) -> None:
    monkeypatch.setenv("EVOLUTION_HMAC_SECRET", SECRET)
    monkeypatch.setenv("EVOLUTION_IP_ALLOWLIST", "9.9.9.9")
    monkeypatch.setenv("WEBHOOK_RATE_LIMIT", "1000/minute")
    from ondeline_api.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(
        "ondeline_api.api.webhook.process_inbound_message_task.delay",
        lambda payload: None,
    )
    from ondeline_api.main import create_app

    app = create_app()
    c = TestClient(app)
    body = json.dumps(PAYLOAD).encode()
    r = c.post("/webhook", content=body, headers={"X-Hub-Signature-256": _sign(body)})
    assert r.status_code == 403
