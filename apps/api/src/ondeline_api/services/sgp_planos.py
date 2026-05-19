"""Lista planos via SGP `/api/ura/consultaplano/` com cache Redis.

Endpoint do SGP retorna:
    {"planos": [{id, grupo, descricao, preco, download, upload, qtd_servicos}, ...]}

App+token vem do `load_sgp_config` (mesmo usado pra consultar cliente).
Cache 1h por provider — planos mudam pouco.
"""
from __future__ import annotations

import json
from typing import Any

import httpx
import redis.asyncio as aioredis
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.services.sgp_config import Provider, load_sgp_config

log = structlog.get_logger(__name__)


_CACHE_TTL = 3600  # 1h


def _cache_key(provider: Provider) -> str:
    return f"sgp:planos:{provider}"


async def listar_planos_sgp(
    session: AsyncSession,
    redis: aioredis.Redis[bytes],
    provider: Provider = "ondeline",
) -> list[dict[str, Any]]:
    """Consulta planos do SGP, com cache Redis 1h.

    Retorna lista [{id, grupo, descricao, preco, download, upload, qtd_servicos}].
    Em caso de erro de transporte, levanta httpx.HTTPError (rota traduz pra 502).
    """
    # 1) Tenta cache.
    try:
        cached = await redis.get(_cache_key(provider))
        if cached:
            return list(json.loads(cached))
    except Exception:
        # Redis fora — segue direto pra fonte. Best effort.
        pass

    # 2) Fonte (SGP).
    cfg = await load_sgp_config(session, provider)
    url = cfg["base_url"].rstrip("/") + "/api/ura/consultaplano/"
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(
            url,
            data={"app": cfg["app"], "token": cfg["token"]},
        )
        r.raise_for_status()
        data = r.json()
    planos = data.get("planos") if isinstance(data, dict) else None
    if not isinstance(planos, list):
        log.warning("sgp.planos.formato_inesperado", data=str(data)[:200])
        planos = []

    # 3) Salva no cache (TTL 1h). Best-effort.
    try:
        await redis.set(_cache_key(provider), json.dumps(planos), ex=_CACHE_TTL)
    except Exception:
        pass

    return planos


async def invalidar_cache(
    redis: aioredis.Redis[bytes],
    provider: Provider = "ondeline",
) -> None:
    """Forca refresh no proximo request."""
    try:
        await redis.delete(_cache_key(provider))
    except Exception:
        pass
