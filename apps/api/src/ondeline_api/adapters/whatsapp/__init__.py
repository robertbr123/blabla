"""Adapters de WhatsApp — Evolution (legado) e Cloud API oficial.

Uso:
    from ondeline_api.adapters.whatsapp import build_for_canal, WhatsAppAdapter

    adapter: WhatsAppAdapter = build_for_canal(canal, settings)
    await adapter.send_text(jid, "oi")

Factory decide qual provider instanciar baseado em ``canal.provider`` (PR2
adiciona essa coluna; por enquanto sempre cai no fallback Evolution).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ondeline_api.adapters.whatsapp.base import (
    SendResult,
    WhatsAppAdapter,
    WhatsAppError,
)
from ondeline_api.adapters.whatsapp.cloud import CloudAdapter, CloudError
from ondeline_api.adapters.whatsapp.evolution import EvolutionAdapter, EvolutionError

if TYPE_CHECKING:
    from ondeline_api.config import Settings
    from ondeline_api.db.models.business import Canal


__all__ = [
    "SendResult",
    "WhatsAppAdapter",
    "WhatsAppError",
    "EvolutionAdapter",
    "EvolutionError",
    "CloudAdapter",
    "CloudError",
    "build_for_canal",
    "build_for_instance",
]


def build_for_canal(canal: "Canal", settings: "Settings") -> WhatsAppAdapter:
    """Devolve o adapter correto pra um Canal.

    PR1: coluna ``canal.provider`` ainda nao existe — sempre devolve Evolution.
    PR2 adiciona a coluna e este factory passa a rotear.
    """
    provider = getattr(canal, "provider", None) or "evolution"
    if provider == "cloud":
        return CloudAdapter(
            access_token=settings.whatsapp_cloud_access_token,
            phone_number_id=str(canal.cloud_phone_id),
            graph_version=settings.whatsapp_cloud_graph_version,
        )
    return EvolutionAdapter(
        base_url=settings.evolution_url,
        instance=canal.evolution_instance,
        api_key=settings.evolution_key,
    )


def build_for_instance(instance: str, settings: "Settings") -> WhatsAppAdapter:
    """Compat com ``services.canal_evolution.evolution_for_instance``.

    Cria EvolutionAdapter direto pelo nome da instancia. Util pra caminhos
    legados que ainda nao tem acesso ao objeto Canal. Sera removido no PR2
    quando todos os call sites passarem a usar ``build_for_canal``.
    """
    return EvolutionAdapter(
        base_url=settings.evolution_url,
        instance=instance,
        api_key=settings.evolution_key,
    )
