"""ConversaRepo: get_or_create por whatsapp + update_estado_status."""
from __future__ import annotations

import pytest
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import (
    Cliente,
    ConversaEstado,
    ConversaStatus,
)
from ondeline_api.repositories.conversa import ConversaRepo

pytestmark = pytest.mark.asyncio


async def test_get_or_create_inserts_when_missing(db_session) -> None:
    repo = ConversaRepo(db_session)
    conversa = await repo.get_or_create_by_whatsapp("5511999@s.whatsapp.net")
    assert conversa.id is not None
    assert conversa.whatsapp == "5511999@s.whatsapp.net"
    assert conversa.estado is ConversaEstado.INICIO
    assert conversa.status is ConversaStatus.BOT


async def test_get_or_create_returns_existing_open_conversa(db_session) -> None:
    repo = ConversaRepo(db_session)
    a = await repo.get_or_create_by_whatsapp("5511888@s.whatsapp.net")
    b = await repo.get_or_create_by_whatsapp("5511888@s.whatsapp.net")
    assert a.id == b.id


async def test_get_or_create_skips_soft_deleted(db_session) -> None:
    repo = ConversaRepo(db_session)
    a = await repo.get_or_create_by_whatsapp("5511777@s.whatsapp.net")
    a.deleted_at = __import__("datetime").datetime.now(tz=__import__("datetime").UTC)
    await db_session.flush()
    b = await repo.get_or_create_by_whatsapp("5511777@s.whatsapp.net")
    assert b.id != a.id


async def test_update_estado_status_persists(db_session) -> None:
    repo = ConversaRepo(db_session)
    c = await repo.get_or_create_by_whatsapp("5511666@s.whatsapp.net")
    await repo.update_estado_status(
        c, estado=ConversaEstado.HUMANO, status=ConversaStatus.AGUARDANDO
    )
    refetched = await repo.get_or_create_by_whatsapp("5511666@s.whatsapp.net")
    assert refetched.id == c.id
    assert refetched.estado is ConversaEstado.HUMANO
    assert refetched.status is ConversaStatus.AGUARDANDO


async def test_link_cliente(db_session) -> None:
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("11122233344"),
        cpf_hash=hash_pii("11122233344"),
        nome_encrypted=encrypt_pii("Maria"),
        whatsapp="5511555@s.whatsapp.net",
    )
    db_session.add(cliente)
    await db_session.flush()

    repo = ConversaRepo(db_session)
    c = await repo.get_or_create_by_whatsapp("5511555@s.whatsapp.net")
    await repo.set_cliente(c, cliente.id)
    refetched = await repo.get_or_create_by_whatsapp("5511555@s.whatsapp.net")
    assert refetched.cliente_id == cliente.id
