"""F1 — Resumo automatico bot->humano."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from ondeline_api.adapters.llm.base import ChatResponse
from ondeline_api.adapters.llm.fakes import FakeLLMProvider
from ondeline_api.db.crypto import decrypt_pii, encrypt_pii
from ondeline_api.repositories.conversa import ConversaRepo
from ondeline_api.repositories.mensagem import MensagemRepo
from ondeline_api.services.handoff_summary import gerar_resumo_handoff

pytestmark = pytest.mark.asyncio


async def _add_cliente_msg(db_session, conversa_id, text: str) -> None:
    repo = MensagemRepo(db_session)
    await repo.insert_inbound_or_skip(
        conversa_id=conversa_id,
        external_id=f"ext-{uuid.uuid4().hex}",
        text=text,
        media_type=None,
        media_url=None,
    )


async def _add_bot_msg(db_session, conversa_id, text: str) -> None:
    repo = MensagemRepo(db_session)
    await repo.insert_bot_reply(conversa_id=conversa_id, text=text)


async def test_gerar_resumo_persiste_fernet_e_timestamp(db_session) -> None:
    repo = ConversaRepo(db_session)
    c = await repo.get_or_create_by_whatsapp("5511aaa@s.whatsapp.net")
    await _add_cliente_msg(db_session, c.id, "Minha internet caiu")
    await _add_bot_msg(db_session, c.id, "Posso ajudar. Qual seu CPF?")
    await _add_cliente_msg(db_session, c.id, "Quero falar com humano")

    fake = FakeLLMProvider(
        [
            ChatResponse(
                content="Cliente sem internet. Bot pediu CPF.\nCliente recusou e pediu humano.",
                tool_calls=[],
                tokens_used=42,
                finish_reason="stop",
            )
        ]
    )

    resumo = await gerar_resumo_handoff(db_session, c.id, fake, model="test-model")
    assert resumo is not None
    assert "sem internet" in resumo.lower()

    await db_session.refresh(c)
    assert c.resumo_handoff_encrypted is not None
    # Fernet roundtrip
    assert decrypt_pii(c.resumo_handoff_encrypted) == resumo
    assert c.resumo_handoff_at is not None


async def test_gerar_resumo_idempotente_sem_novas_mensagens(db_session) -> None:
    repo = ConversaRepo(db_session)
    c = await repo.get_or_create_by_whatsapp("5511bbb@s.whatsapp.net")
    await _add_cliente_msg(db_session, c.id, "oi")
    c.resumo_handoff_encrypted = encrypt_pii("resumo antigo")
    c.resumo_handoff_at = datetime.now(tz=UTC)
    await db_session.flush()

    fake = FakeLLMProvider([])  # nao deve chamar o LLM
    resumo = await gerar_resumo_handoff(db_session, c.id, fake, model="test-model")
    assert resumo is None
    assert fake.calls == []
    # resumo antigo preservado
    await db_session.refresh(c)
    assert decrypt_pii(c.resumo_handoff_encrypted) == "resumo antigo"


async def test_gerar_resumo_regenera_apos_5_mensagens_novas(db_session) -> None:
    repo = ConversaRepo(db_session)
    c = await repo.get_or_create_by_whatsapp("5511ccc@s.whatsapp.net")
    old_ts = datetime.now(tz=UTC) - timedelta(hours=1)
    c.resumo_handoff_encrypted = encrypt_pii("resumo antigo")
    c.resumo_handoff_at = old_ts
    await db_session.flush()
    # 5 mensagens novas (depois do resumo antigo)
    for i in range(5):
        await _add_cliente_msg(db_session, c.id, f"msg {i}")

    fake = FakeLLMProvider(
        [
            ChatResponse(
                content="Resumo atualizado",
                tool_calls=[],
                tokens_used=10,
                finish_reason="stop",
            )
        ]
    )
    resumo = await gerar_resumo_handoff(db_session, c.id, fake, model="test-model")
    assert resumo == "Resumo atualizado"
    await db_session.refresh(c)
    assert decrypt_pii(c.resumo_handoff_encrypted) == "Resumo atualizado"


async def test_gerar_resumo_llm_falha_nao_quebra(db_session) -> None:
    repo = ConversaRepo(db_session)
    c = await repo.get_or_create_by_whatsapp("5511ddd@s.whatsapp.net")
    await _add_cliente_msg(db_session, c.id, "oi")

    class _BrokenProvider(FakeLLMProvider):
        async def chat(self, req):  # type: ignore[override]
            raise RuntimeError("hermes offline")

    broken = _BrokenProvider([])
    resumo = await gerar_resumo_handoff(db_session, c.id, broken, model="test-model")
    assert resumo is None
    await db_session.refresh(c)
    assert c.resumo_handoff_encrypted is None
    assert c.resumo_handoff_at is None


async def test_gerar_resumo_sem_mensagens_retorna_none(db_session) -> None:
    repo = ConversaRepo(db_session)
    c = await repo.get_or_create_by_whatsapp("5511eee@s.whatsapp.net")
    fake = FakeLLMProvider([])
    resumo = await gerar_resumo_handoff(db_session, c.id, fake, model="test-model")
    assert resumo is None
    assert fake.calls == []
