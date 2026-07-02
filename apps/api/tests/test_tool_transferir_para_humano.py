"""Tool transferir_para_humano — atualiza status da conversa."""
from __future__ import annotations

from uuid import uuid4

import pytest
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import (
    Cliente,
    Conversa,
    ConversaEstado,
    ConversaStatus,
    Lead,
)
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.transferir_para_humano import (
    SCHEMA,
    transferir_para_humano,
)
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def test_marca_conversa_aguardando(db_session) -> None:
    conv = Conversa(
        id=uuid4(),
        whatsapp="5511@s",
        estado=ConversaEstado.CLIENTE,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()
    ctx = ToolContext(
        session=db_session,
        conversa=conv,
        cliente=None,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=None,  # type: ignore[arg-type]
    )
    out = await transferir_para_humano(ctx, motivo="quer falar com humano")
    assert out["ok"] is True
    assert out["motivo"] == "quer falar com humano"
    await db_session.flush()
    assert conv.status is ConversaStatus.AGUARDANDO
    assert conv.estado is ConversaEstado.AGUARDA_ATENDENTE


async def test_transferir_nao_cliente_cria_lead(db_session) -> None:
    """Prospect (sem cliente_id) que chega no atendente vira lead automaticamente."""
    jid = f"5592{uuid4().hex[:9]}@s.whatsapp.net"
    conv = Conversa(
        id=uuid4(),
        whatsapp=jid,
        estado=ConversaEstado.INICIO,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()
    ctx = ToolContext(
        session=db_session,
        conversa=conv,
        cliente=None,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=None,  # type: ignore[arg-type]
    )
    await transferir_para_humano(ctx, motivo="quer ser cliente")
    await db_session.flush()
    leads = list(
        (await db_session.execute(select(Lead).where(Lead.whatsapp == jid))).scalars().all()
    )
    assert len(leads) == 1
    assert leads[0].interesse == "quer ser cliente"


async def test_transferir_cliente_identificado_nao_cria_lead(db_session) -> None:
    """Cliente ja identificado (cliente_id setado) NAO vira lead."""
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
        cliente_id=cliente.id,
        estado=ConversaEstado.CLIENTE,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()
    ctx = ToolContext(
        session=db_session,
        conversa=conv,
        cliente=cliente,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=None,  # type: ignore[arg-type]
    )
    await transferir_para_humano(ctx, motivo="suporte")
    await db_session.flush()
    leads = list(
        (await db_session.execute(select(Lead).where(Lead.whatsapp == jid))).scalars().all()
    )
    assert len(leads) == 0


def test_schema_estavel() -> None:
    assert SCHEMA["type"] == "object"
    assert "motivo" in SCHEMA["properties"]
