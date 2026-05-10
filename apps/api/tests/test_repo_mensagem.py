"""MensagemRepo: insercao idempotente via UNIQUE(external_id, created_at) +
inseridor de resposta do bot.
"""
from __future__ import annotations

import pytest
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import MensagemRole
from ondeline_api.repositories.conversa import ConversaRepo
from ondeline_api.repositories.mensagem import MensagemRepo

pytestmark = pytest.mark.asyncio


async def test_insert_inbound_persists(db_session) -> None:
    conv = await ConversaRepo(db_session).get_or_create_by_whatsapp("5511aaa@s.whatsapp.net")
    repo = MensagemRepo(db_session)
    inserted = await repo.insert_inbound_or_skip(
        conversa_id=conv.id,
        external_id="WAEVT_1",
        text="Olá",
        media_type=None,
        media_url=None,
    )
    assert inserted is not None
    assert inserted.role is MensagemRole.CLIENTE
    assert inserted.content_encrypted is not None
    assert decrypt_pii(inserted.content_encrypted) == "Olá"


async def test_insert_inbound_dedup_returns_none(db_session) -> None:
    conv = await ConversaRepo(db_session).get_or_create_by_whatsapp("5511bbb@s.whatsapp.net")
    repo = MensagemRepo(db_session)
    a = await repo.insert_inbound_or_skip(
        conversa_id=conv.id, external_id="WAEVT_2", text="oi", media_type=None, media_url=None
    )
    assert a is not None
    b = await repo.insert_inbound_or_skip(
        conversa_id=conv.id, external_id="WAEVT_2", text="oi de novo", media_type=None, media_url=None
    )
    assert b is None  # duplicado


async def test_insert_inbound_media_only(db_session) -> None:
    conv = await ConversaRepo(db_session).get_or_create_by_whatsapp("5511ccc@s.whatsapp.net")
    repo = MensagemRepo(db_session)
    m = await repo.insert_inbound_or_skip(
        conversa_id=conv.id,
        external_id="WAEVT_3",
        text=None,
        media_type="image",
        media_url=None,
    )
    assert m is not None
    assert m.content_encrypted is None
    assert m.media_type == "image"


async def test_insert_bot_reply_is_role_bot(db_session) -> None:
    conv = await ConversaRepo(db_session).get_or_create_by_whatsapp("5511ddd@s.whatsapp.net")
    repo = MensagemRepo(db_session)
    msg = await repo.insert_bot_reply(conversa_id=conv.id, text="Recebido!")
    assert msg.role is MensagemRole.BOT
    assert msg.external_id is None
    assert msg.content_encrypted is not None
    assert decrypt_pii(msg.content_encrypted) == "Recebido!"
