"""Tool: busca cliente nos provedores SGP via cache.

Atualiza o `Cliente` no DB e vincula `Conversa.cliente_id`. Retorna dict
mascarado para o LLM (nao vaza CPF, mantem nome/plano/cidade/status mes).
"""
from __future__ import annotations

from typing import Any

from ondeline_api.adapters.sgp.base import Fatura
from ondeline_api.repositories.cliente import ClienteRepo
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cpf_cnpj": {
            "type": "string",
            "description": "CPF ou CNPJ; pontuacao opcional (sera limpa).",
        }
    },
    "required": ["cpf_cnpj"],
}


def _resumo_titulos(titulos: list[Fatura]) -> dict[str, Any]:
    abertos = [t for t in titulos if t.status == "aberto"]
    return {
        "abertos": len(abertos),
        "vencimentos": [t.vencimento for t in abertos[:3]],
    }


@tool(
    name="buscar_cliente_sgp",
    description=(
        "Consulta cliente nos provedores SGP (Ondeline + LinkNetAM, nessa ordem). "
        "Use quando o cliente informar CPF ou CNPJ. Retorna nome, plano, status, "
        "cidade e resumo de faturas em aberto."
    ),
    parameters=SCHEMA,
)
async def buscar_cliente_sgp(ctx: ToolContext, *, cpf_cnpj: str) -> dict[str, Any]:
    cli_sgp = await ctx.sgp_cache.get_cliente(cpf_cnpj)
    if cli_sgp is None:
        return {"encontrado": False}

    cliente_db = await ClienteRepo(ctx.session).upsert_from_sgp(
        cli_sgp, whatsapp=ctx.conversa.whatsapp
    )
    ctx.conversa.cliente_id = cliente_db.id
    await ctx.session.flush()

    contrato = cli_sgp.contratos[0] if cli_sgp.contratos else None
    return {
        "encontrado": True,
        "nome": cli_sgp.nome,
        "plano": contrato.plano if contrato else None,
        "status_contrato": contrato.status if contrato else None,
        "motivo_status": contrato.motivo_status if contrato else None,
        "cidade": (contrato.cidade if contrato and contrato.cidade else cli_sgp.endereco.cidade),
        "faturas": _resumo_titulos(cli_sgp.titulos),
    }
