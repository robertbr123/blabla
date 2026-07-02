"""Tool registrar_lead — bot registra prospect interessado como lead."""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
    Lead,
)
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registrar_lead import SCHEMA, registrar_lead

pytestmark = pytest.mark.asyncio


def _ctx(db_session, conv) -> ToolContext:
    return ToolContext(
        session=db_session,
        conversa=conv,
        cliente=None,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=None,  # type: ignore[arg-type]
    )


async def test_registrar_lead_cria(db_session) -> None:
    jid = f"5592{uuid4().hex[:9]}@s.whatsapp.net"
    conv = Conversa(
        id=uuid4(), whatsapp=jid, estado=ConversaEstado.INICIO, status=ConversaStatus.BOT
    )
    db_session.add(conv)
    await db_session.flush()
    out = await registrar_lead(_ctx(db_session, conv), nome="João Pedro", interesse="fibra 500MB")
    assert out["ok"] is True
    await db_session.flush()
    lead = (
        await db_session.execute(select(Lead).where(Lead.whatsapp == jid))
    ).scalar_one()
    assert lead.nome == "João Pedro"
    assert lead.interesse == "fibra 500MB"


async def test_registrar_lead_ignora_se_ja_cliente(db_session) -> None:
    from ondeline_api.db.crypto import encrypt_pii, hash_pii
    from ondeline_api.db.models.business import Cliente

    jid = f"5592{uuid4().hex[:9]}@s.whatsapp.net"
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("11122233344"),
        cpf_hash=hash_pii(uuid4().hex),
        nome_encrypted=encrypt_pii("Cliente Real"),
        whatsapp=jid,
    )
    db_session.add(cliente)
    await db_session.flush()
    conv = Conversa(
        id=uuid4(),
        whatsapp=jid,
        cliente_id=cliente.id,  # ja identificado
        estado=ConversaEstado.CLIENTE,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()
    out = await registrar_lead(_ctx(db_session, conv), nome="Fulano", interesse=None)
    assert out["ok"] is False
    leads = list(
        (await db_session.execute(select(Lead).where(Lead.whatsapp == jid))).scalars().all()
    )
    assert len(leads) == 0


def test_schema_tem_nome() -> None:
    assert SCHEMA["type"] == "object"
    assert "nome" in SCHEMA["properties"]
