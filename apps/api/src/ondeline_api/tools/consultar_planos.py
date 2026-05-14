"""Tool: consultar planos disponiveis (lidos do Config['planos'])."""
from __future__ import annotations

from typing import Any

from ondeline_api.repositories.config import ConfigRepo
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool

SCHEMA: dict[str, Any] = {"type": "object", "properties": {}}

_DEFAULT_PLANOS = [
    {
        "nome": "Essencial",
        "preco": 110.0,
        "velocidade": "35MB",
        "extras": [],
        "descricao": "",
        "ativo": True,
        "destaque": False,
    },
    {
        "nome": "Plus",
        "preco": 130.0,
        "velocidade": "55MB",
        "extras": ["IPTV gratis"],
        "descricao": "",
        "ativo": True,
        "destaque": True,
    },
    {
        "nome": "Premium",
        "preco": 150.0,
        "velocidade": "55MB",
        "extras": ["IPTV", "camera comodato"],
        "descricao": "",
        "ativo": True,
        "destaque": False,
    },
]


@tool(
    name="consultar_planos",
    description="Retorna a lista de planos de internet disponiveis com preco e velocidade.",
    parameters=SCHEMA,
)
async def consultar_planos(ctx: ToolContext) -> dict[str, Any]:
    repo = ConfigRepo(ctx.session)
    raw = await repo.get("planos")
    planos = raw if isinstance(raw, list) else _DEFAULT_PLANOS
    planos_ativos = [p for p in planos if p.get("ativo", True)]
    return {"planos": planos_ativos, "pagamento": ["PIX", "Boleto"]}
