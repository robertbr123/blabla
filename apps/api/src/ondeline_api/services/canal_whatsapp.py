"""F4 / Cloud-API — resolve qual WhatsAppAdapter usar pra uma Conversa.

Substitui ``services.canal_evolution`` mas mantem o modulo antigo como shim
de re-export pra nao quebrar workers legados (outbound/asr_jobs/llm_turn).

API nova (provider-aware):
- ``adapter_for_conversa(session, conversa_id, settings)`` — devolve
  ``WhatsAppAdapter`` (Evolution OU Cloud) baseado em ``canal.provider``.
- ``adapter_for_canal(canal, settings)`` — quando ja se tem o objeto Canal.

API legada (mantida pra compat, so faz sentido pra canais Evolution):
- ``resolver_instance(...)`` — devolve string com nome da instancia Evolution.
- ``evolution_for_instance(...)`` — cria EvolutionAdapter direto.

Estrategia falha-aberta: se algo der errado no lookup, cai no canal default
(settings.evolution_instance / provider=evolution).
"""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.whatsapp import (
    EvolutionAdapter,
    WhatsAppAdapter,
    build_for_canal,
    build_for_instance,
)
from ondeline_api.config import Settings
from ondeline_api.db.models.business import Canal, Conversa

log = structlog.get_logger(__name__)


async def adapter_for_conversa(
    session: AsyncSession, conversa_id: UUID, settings: Settings
) -> WhatsAppAdapter:
    """Devolve o WhatsAppAdapter correto pra ``conversa_id``.

    Falha-aberta: se a conversa nao tem canal_id, ou o canal nao existe,
    devolve EvolutionAdapter apontando pra ``settings.evolution_instance``.
    """
    try:
        stmt = (
            select(Canal)
            .select_from(Conversa)
            .join(Canal, Canal.id == Conversa.canal_id)
            .where(Conversa.id == conversa_id)
        )
        canal = (await session.execute(stmt)).scalar_one_or_none()
        if canal is not None:
            return build_for_canal(canal, settings)
    except Exception as e:
        log.warning(
            "canal.adapter_for_conversa_failed",
            conversa_id=str(conversa_id),
            error=str(e),
        )
    return build_for_instance(settings.evolution_instance, settings)


def adapter_for_canal(canal: Canal, settings: Settings) -> WhatsAppAdapter:
    """Wrapper sobre ``adapters.whatsapp.build_for_canal``."""
    return build_for_canal(canal, settings)


# ─────────────────────────────────────────────────────────────
# Compat: API legada (Evolution-only). Mantida ate os call sites migrarem.
# ─────────────────────────────────────────────────────────────


async def resolver_instance(
    session: AsyncSession, conversa_id: UUID, settings: Settings
) -> str:
    """Retorna o nome da instancia Evolution a usar para ``conversa_id``.

    DEPRECATED: usa ``adapter_for_conversa`` em codigo novo. Esta funcao so
    funciona corretamente pra canais com ``provider='evolution'`` — pra canais
    Cloud ela devolve a instancia default (falha-aberta).
    """
    try:
        stmt = (
            select(Canal.evolution_instance, Canal.provider)
            .select_from(Conversa)
            .join(Canal, Canal.id == Conversa.canal_id)
            .where(Conversa.id == conversa_id)
        )
        row = (await session.execute(stmt)).first()
        if row and row.provider == "evolution" and row.evolution_instance:
            return str(row.evolution_instance)
    except Exception as e:
        log.warning(
            "canal.resolver_instance_failed",
            conversa_id=str(conversa_id),
            error=str(e),
        )
    return settings.evolution_instance


def evolution_for_instance(instance: str, settings: Settings) -> EvolutionAdapter:
    """DEPRECATED: cria EvolutionAdapter apontando pra ``instance``.

    Mantida pra compat com workers que ainda usam o par
    ``resolver_instance`` + ``evolution_for_instance``. Codigo novo deve usar
    ``adapter_for_conversa`` (provider-aware).
    """
    return EvolutionAdapter(
        base_url=settings.evolution_url,
        instance=instance,
        api_key=settings.evolution_key,
    )
