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


def _nome_fallback(whatsapp: str) -> str:
    """Nome-placeholder pra lead sem nome real: 'Contato (92) 9XXXX-XXXX'.

    O prefixo 'Contato ' é o que permite ao upsert promover pro nome real
    quando o bot coletar (via tool registrar_lead). Sem número reconhecível,
    devolve 'Contato' + o que sobrar dos dígitos.
    """
    digits = "".join(c for c in whatsapp if c.isdigit())
    local = digits[2:] if digits.startswith("55") and len(digits) >= 12 else digits
    if len(local) == 11:
        fmt = f"({local[:2]}) {local[2:3]} {local[3:7]}-{local[7:]}"
    elif len(local) == 10:
        fmt = f"({local[:2]}) {local[2:6]}-{local[6:]}"
    else:
        fmt = local or whatsapp
    return f"Contato {fmt}"


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
    prev_status = ctx.conversa.status
    ctx.conversa.estado = ConversaEstado.AGUARDA_ATENDENTE
    ctx.conversa.status = ConversaStatus.AGUARDANDO
    if ctx.conversa.transferred_at is None:
        ctx.conversa.transferred_at = datetime.now(tz=UTC)
    await ctx.session.flush()

    # Captura de lead: prospect (nao identificado como cliente) que chega no
    # atendente vira lead automaticamente. Idempotente (upsert por whatsapp) —
    # se o bot ja registrou via registrar_lead, so complementa. Best-effort:
    # falha aqui nao pode quebrar a transferencia.
    if ctx.conversa.cliente_id is None:
        try:
            from ondeline_api.repositories.lead import LeadRepo

            await LeadRepo(ctx.session).upsert_by_whatsapp(
                whatsapp=ctx.conversa.whatsapp,
                nome=_nome_fallback(ctx.conversa.whatsapp),
                interesse=motivo,
            )
        except Exception:
            pass

    # Enfileira resumo do handoff (F1) — best effort, nao bloqueia a tool.
    if prev_status is not ConversaStatus.AGUARDANDO:
        try:
            from ondeline_api.workers.handoff_summary_task import handoff_summary_task

            handoff_summary_task.delay(conversa_id=str(ctx.conversa.id))
        except Exception:
            pass
    return {"ok": True, "motivo": motivo}
