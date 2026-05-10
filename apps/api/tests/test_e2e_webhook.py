"""E2E: POST /webhook -> task eager -> DB tem cliente_msg + resposta do bot.

Note: The test is *synchronous* intentionally.  The Celery task uses
``asyncio.run()`` internally; if the test itself were async (under
pytest-asyncio) there would already be a running event loop and
``asyncio.run()`` would raise RuntimeError.  Running the test sync avoids
that conflict while still allowing us to call ``asyncio.run()`` for the
DB-assertion coroutine after the webhook POST returns.

M4 flow: webhook -> process_inbound_message_task (eager) -> enfileira
llm_turn_task (eager) -> chama Hermes (nao mockado -> falha) ->
_force_escalate -> manda fallback via Evolution (mockado) + persiste BOT msg.
Por isso o estado final e AGUARDA_ATENDENTE (nao HUMANO como em M3).
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac as _hmac
import json
import uuid

import pytest
import respx
from fastapi.testclient import TestClient
from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
    Mensagem,
    MensagemRole,
)
from ondeline_api.workers.celery_app import celery_app
from sqlalchemy import select

SECRET = "e2e-secret-42"


def _sign(body: bytes) -> str:
    return f"sha256={_hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()}"


@pytest.fixture(autouse=True)
def _eager(monkeypatch) -> None:
    monkeypatch.setenv("EVOLUTION_HMAC_SECRET", SECRET)
    monkeypatch.setenv("EVOLUTION_URL", "http://evo.test")
    monkeypatch.setenv("EVOLUTION_INSTANCE", "hermes-wa")
    monkeypatch.setenv("EVOLUTION_KEY", "fake-key")
    monkeypatch.setenv("WEBHOOK_RATE_LIMIT", "1000/minute")
    from ondeline_api.config import get_settings

    get_settings.cache_clear()
    celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)


def test_webhook_to_db_full_flow() -> None:
    # Use unique JID per test run to avoid clashes with leftover data in shared dev DB
    jid = f"5511444{uuid.uuid4().hex[:6]}@s.whatsapp.net"
    eid = f"WAEVT_E2E_{uuid.uuid4().hex[:8]}"

    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "id": eid,
                "remoteJid": jid,
                "fromMe": False,
            },
            "pushName": "Joao",
            "message": {"conversation": "Tô sem internet"},
        },
    }
    body = json.dumps(payload).encode()

    with respx.mock(assert_all_called=True) as router:
        router.post("http://evo.test/message/sendText/hermes-wa").respond(
            200, json={"key": {"id": "OUT_1"}}
        )
        from ondeline_api.main import create_app

        app = create_app()
        c = TestClient(app)
        r = c.post(
            "/webhook", content=body, headers={"X-Hub-Signature-256": _sign(body)}
        )
        assert r.status_code == 202

    # The Celery tasks committed via task_session() (independent connections).
    # Open a fresh session via get_sessionmaker() to read the committed data.
    # We use asyncio.run() here because the test is sync (no event loop running).
    # Reset engine cache first: the tasks ran in threads with their own event loops
    # and each reset/created a pool for that loop. We need a fresh pool for this loop.
    from ondeline_api.db.engine import reset_engine_cache

    reset_engine_cache()

    async def _assert_db() -> None:
        from ondeline_api.db.engine import get_sessionmaker

        sm = get_sessionmaker()
        async with sm() as session:
            conv_row = (
                await session.execute(
                    select(Conversa).where(Conversa.whatsapp == jid)
                )
            ).scalar_one()
            # M4: LLM falha (Hermes nao mockado) -> _force_escalate -> AGUARDA_ATENDENTE
            assert conv_row.estado is ConversaEstado.AGUARDA_ATENDENTE
            assert conv_row.status is ConversaStatus.AGUARDANDO

            msgs = (
                await session.execute(
                    select(Mensagem)
                    .where(Mensagem.conversa_id == conv_row.id)
                    .order_by(Mensagem.created_at)
                )
            ).scalars().all()
            roles = [m.role for m in msgs]
            assert roles == [MensagemRole.CLIENTE, MensagemRole.BOT]

    asyncio.run(_assert_db())
