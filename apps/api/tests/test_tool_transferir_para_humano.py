"""Tool transferir_para_humano — atualiza status da conversa."""
from __future__ import annotations

from uuid import uuid4

import pytest
from ondeline_api.db.models.business import Conversa, ConversaEstado, ConversaStatus
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.transferir_para_humano import (
    SCHEMA,
    transferir_para_humano,
)

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


def test_schema_estavel() -> None:
    assert SCHEMA["type"] == "object"
    assert "motivo" in SCHEMA["properties"]
