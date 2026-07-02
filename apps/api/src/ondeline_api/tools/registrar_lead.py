"""Tool: registrar um interessado (lead) que quer virar cliente."""
from __future__ import annotations

from typing import Any

from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "nome": {
            "type": "string",
            "description": "Nome do interessado (pergunte antes se nao souber).",
        },
        "interesse": {
            "type": "string",
            "description": (
                "O que a pessoa quer, em poucas palavras "
                "(ex: 'plano 500MB', 'fibra no bairro Centro')."
            ),
        },
    },
    "required": ["nome"],
}


@tool(
    name="registrar_lead",
    description=(
        "Registra um interessado (lead) que NAO e cliente e quer contratar. "
        "Use quando alguem demonstra interesse em virar cliente — colete o "
        "nome antes de chamar. Nao use para clientes ja identificados."
    ),
    parameters=SCHEMA,
)
async def registrar_lead(
    ctx: ToolContext, *, nome: str, interesse: str | None = None
) -> dict[str, Any]:
    # Guarda: so registra prospect. Cliente identificado nao vira lead.
    if ctx.conversa.cliente_id is not None:
        return {"ok": False, "motivo": "ja e cliente identificado"}

    from ondeline_api.repositories.lead import LeadRepo

    lead, created = await LeadRepo(ctx.session).upsert_by_whatsapp(
        whatsapp=ctx.conversa.whatsapp,
        nome=nome,
        interesse=interesse,
    )
    return {"ok": True, "lead_id": str(lead.id), "novo": created}
