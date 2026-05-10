"""Tool: lista manutencoes planejadas que afetam uma cidade."""
from __future__ import annotations

from typing import Any

from ondeline_api.repositories.manutencao import ManutencaoRepo
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"cidade": {"type": "string"}},
    "required": ["cidade"],
}


@tool(
    name="consultar_manutencoes",
    description="Verifica manutencoes planejadas em andamento que afetam uma cidade.",
    parameters=SCHEMA,
)
async def consultar_manutencoes(ctx: ToolContext, *, cidade: str) -> dict[str, Any]:
    repo = ManutencaoRepo(ctx.session)
    items = await repo.list_active_in_cidade(cidade)
    return {
        "manutencoes": [
            {
                "titulo": m.titulo,
                "descricao": m.descricao,
                "inicio_at": m.inicio_at.isoformat(),
                "fim_at": m.fim_at.isoformat(),
            }
            for m in items
        ]
    }
