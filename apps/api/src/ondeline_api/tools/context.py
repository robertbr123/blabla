"""ToolContext — bundle de dependencias passado a cada execucao de tool.

Tools sao funcoes puras (`async def(ctx, **args) -> dict`) sem estado proprio;
recebem tudo via `ctx`. Isso facilita teste (passar fakes) e swap de provider.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.models.business import Cliente, Conversa
from ondeline_api.services.sgp_cache import SgpCacheService


@dataclass
class ToolContext:
    session: AsyncSession
    conversa: Conversa
    cliente: Cliente | None
    evolution: EvolutionAdapter
    sgp_router: SgpRouter
    sgp_cache: SgpCacheService
