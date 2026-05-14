"""Tool: inicia coleta de novo endereco para mudanca de instalacao."""
from __future__ import annotations

from typing import Any

from ondeline_api.db.models.business import ConversaEstado, ConversaStatus
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool

SCHEMA: dict[str, Any] = {"type": "object", "properties": {}, "required": []}


@tool(
    name="iniciar_mudanca_endereco",
    description=(
        "Use quando o cliente quiser mudar o endereço de instalação. "
        "Inicia coleta estruturada do novo endereço. "
        "NAO use para outros assuntos."
    ),
    parameters=SCHEMA,
)
async def iniciar_mudanca_endereco(ctx: ToolContext) -> dict[str, Any]:
    from datetime import UTC, datetime

    ctx.conversa.estado = ConversaEstado.MUDANCA_ENDERECO
    ctx.conversa.checklist_metadata = {
        "step": "rua",
        "novo_endereco": {},
        "iniciado_em": datetime.now(tz=UTC).isoformat(),
    }
    await ctx.session.flush()
    return {
        "ok": True,
        "proxima_pergunta": "Qual é o novo endereço? Informe a rua e o número.",
    }
