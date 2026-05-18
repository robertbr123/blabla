"""F4 — resolve qual instância Evolution usar pra uma dada Conversa.

Outbound workers (send_outbound, llm_turn, cobranca, etc) chamam
``evolution_for_conversa`` pra criar um EvolutionAdapter apontando pra
instância correta. Se a conversa não tem ``canal_id`` (legado) ou se o canal
foi removido, usa o default (settings.evolution_instance).
"""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.config import Settings
from ondeline_api.db.models.business import Canal, Conversa

log = structlog.get_logger(__name__)


async def resolver_instance(
    session: AsyncSession, conversa_id: UUID, settings: Settings
) -> str:
    """Retorna o nome da instância Evolution a usar para `conversa_id`.

    Falha-aberta: se algo der errado, usa ``settings.evolution_instance``.
    """
    try:
        stmt = (
            select(Canal.evolution_instance)
            .select_from(Conversa)
            .join(Canal, Canal.id == Conversa.canal_id)
            .where(Conversa.id == conversa_id)
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row:
            return str(row)
    except Exception as e:
        log.warning("canal.resolver_instance_failed", conversa_id=str(conversa_id), error=str(e))
    return settings.evolution_instance


def evolution_for_instance(instance: str, settings: Settings) -> EvolutionAdapter:
    """Cria um EvolutionAdapter apontando pra `instance` informado."""
    return EvolutionAdapter(
        base_url=settings.evolution_url,
        instance=instance,
        api_key=settings.evolution_key,
    )
