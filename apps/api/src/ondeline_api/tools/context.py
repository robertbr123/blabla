"""ToolContext — bundle de dependencias passado a cada execucao de tool.

Tools sao funcoes puras (`async def(ctx, **args) -> dict`) sem estado proprio;
recebem tudo via `ctx`. Isso facilita teste (passar fakes) e swap de provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.adapters.whatsapp import WhatsAppAdapter
from ondeline_api.db.models.business import Cliente, Conversa
from ondeline_api.services.sgp_cache import SgpCacheService


@dataclass
class ToolContext:
    session: AsyncSession
    conversa: Conversa
    cliente: Cliente | None
    # Campo mantem nome 'evolution' por compat com 5+ call sites em
    # services/llm_loop.py e tools/*.py. Aceita qualquer WhatsAppAdapter
    # (Evolution ou Cloud) — todos os metodos chamados (send_text,
    # send_media, send_media_bytes) estao no Protocol.
    evolution: WhatsAppAdapter
    sgp_router: SgpRouter
    sgp_cache: SgpCacheService
    # F11 — redis opcional pra rate-limit/cache de tools (ex: nao reenviar
    # boleto da mesma fatura por 20min). Tools chamam getattr(ctx, 'redis', None)
    # pra ser tolerante quando rodam em contexto sem Redis (testes).
    redis: Any = field(default=None)
