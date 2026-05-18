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


async def test_list_paginated_returns_nome_encrypted_when_cliente_linked(
    db_session,
) -> None:
    """F0: lista de conversas devolve nome do cliente (Fernet) quando vinculado."""
    from ondeline_api.db.crypto import decrypt_pii

    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("22233344455"),
        cpf_hash=hash_pii("22233344455"),
        nome_encrypted=encrypt_pii("João Silva"),
        whatsapp="5511444@s.whatsapp.net",
    )
    db_session.add(cliente)
    await db_session.flush()

    repo = ConversaRepo(db_session)
    c = await repo.get_or_create_by_whatsapp("5511444@s.whatsapp.net")
    await repo.set_cliente(c, cliente.id)

    rows, _ = await repo.list_paginated(q="5511444")
    assert len(rows) == 1
    conv, nome_enc = rows[0]
    assert conv.id == c.id
    assert nome_enc is not None
    assert decrypt_pii(nome_enc) == "João Silva"


async def test_list_paginated_returns_none_nome_when_no_cliente(db_session) -> None:
    """F0: conversa sem cliente vinculado devolve nome_encrypted=None."""
    repo = ConversaRepo(db_session)
    await repo.get_or_create_by_whatsapp("5511333@s.whatsapp.net")

    rows, _ = await repo.list_paginated(q="5511333")
    assert len(rows) == 1
    _conv, nome_enc = rows[0]
    assert nome_enc is None
