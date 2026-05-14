"""Tool: transferir conversa para atendente humano."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ondeline_api.db.models.business import ConversaEstado, ConversaStatus
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "motivo": {
            "type": "string",
            "description": "Motivo curto (ex: 'cliente pediu cancelamento').",
        }
    },
    "required": ["motivo"],
}


@tool(
    name="transferir_para_humano",
    description=(
        "Marca a conversa como aguardando atendente humano. "
        "Use quando o cliente insistir em humano OU quando voce nao "
        "conseguir resolver."
    ),
    parameters=SCHEMA,
)
async def transferir_para_humano(ctx: ToolContext, *, motivo: str) -> dict[str, Any]:
    ctx.conversa.estado = ConversaEstado.AGUARDA_ATENDENTE
    ctx.conversa.status = ConversaStatus.AGUARDANDO
    if ctx.conversa.transferred_at is None:
        ctx.conversa.transferred_at = datetime.now(tz=UTC)
    await ctx.session.flush()
    return {"ok": True, "motivo": motivo}
