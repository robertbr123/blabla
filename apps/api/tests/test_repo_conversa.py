"""ConversaRepo: get_or_create por whatsapp + update_estado_status."""
from __future__ import annotations

import uuid as _uuid

import pytest
from ondeline_api.db.crypto import decrypt_pii, encrypt_pii, hash_pii
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
    """F0: lista de conversas devolve nome do cliente (Fernet) quando vinculado.

    JID unico (uuid) pra garantir isolamento do filtro `q` mesmo se o ambiente
    tiver outras conversas residuais.
    """
    jid_slug = _uuid.uuid4().hex[:10]
    jid = f"{jid_slug}@s.whatsapp.net"

    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("22233344455"),
        cpf_hash=hash_pii("22233344455"),
        nome_encrypted=encrypt_pii("João Silva"),
        whatsapp=jid,
    )
    db_session.add(cliente)
    await db_session.flush()

    repo = ConversaRepo(db_session)
    c = await repo.get_or_create_by_whatsapp(jid)
    await repo.set_cliente(c, cliente.id)

    rows, _ = await repo.list_paginated(q=jid_slug)
    # Filtra pela conversa que estamos verificando (defensivo se houver outras
    # conversas no DB de test que casem por substring do JID).
    matching = [(conv, nome_enc) for conv, nome_enc in rows if conv.id == c.id]
    assert len(matching) == 1
    _conv, nome_enc = matching[0]
    assert nome_enc is not None
    assert decrypt_pii(nome_enc) == "João Silva"


async def test_list_paginated_returns_none_nome_when_no_cliente(db_session) -> None:
    """F0: conversa sem cliente vinculado devolve nome_encrypted=None."""
    jid_slug = _uuid.uuid4().hex[:10]
    jid = f"{jid_slug}@s.whatsapp.net"

    repo = ConversaRepo(db_session)
    c = await repo.get_or_create_by_whatsapp(jid)

    rows, _ = await repo.list_paginated(q=jid_slug)
    matching = [(conv, nome_enc) for conv, nome_enc in rows if conv.id == c.id]
    assert len(matching) == 1
    _conv, nome_enc = matching[0]
    assert nome_enc is None


async def test_list_paginated_cursor_nao_pula_item_na_fronteira(db_session) -> None:
    """Regressão: a paginação não pode perder o item da fronteira entre páginas.

    O cursor deve ser o último item RETORNADO (não o espiado); com o filtro
    estrito `< cursor`, a próxima página inclui o item seguinte sem pular.
    """
    from datetime import UTC, datetime, timedelta

    slug = _uuid.uuid4().hex[:10]
    repo = ConversaRepo(db_session)
    c1 = await repo.get_or_create_by_whatsapp(f"{slug}1@s.whatsapp.net")
    c2 = await repo.get_or_create_by_whatsapp(f"{slug}2@s.whatsapp.net")
    # timestamps distintos e determinísticos (ordena por last_message_at desc)
    now = datetime.now(tz=UTC)
    c1.last_message_at = now
    c2.last_message_at = now - timedelta(minutes=1)
    await db_session.flush()

    # página 1 (limit 1) → a mais recente + cursor
    page1, cur = await repo.list_paginated(q=slug, limit=1)
    assert [conv.id for conv, _ in page1] == [c1.id]
    assert cur is not None

    # página 2 com o cursor → a próxima (c2), SEM pular
    page2, _cur2 = await repo.list_paginated(q=slug, limit=1, cursor=cur)
    assert [conv.id for conv, _ in page2] == [c2.id]
