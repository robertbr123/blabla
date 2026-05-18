"""Task Celery: roda a régua de cobrança diariamente (F2).

Beat-triggered as 09:00 BRT. Fila `notifications` pra nao competir com filas
de bot (`default`/`llm`).
"""
from __future__ import annotations

from typing import Any, cast

import structlog

from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.adapters.sgp.linknetam import SgpLinkNetAMProvider
from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.config import get_settings
from ondeline_api.services.cobranca_regua import run_regua
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.services.sgp_config import load_sgp_config
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import get_redis, run_task, task_session

log = structlog.get_logger(__name__)


async def _run() -> dict[str, int]:
    s = get_settings()
    redis = await get_redis()
    evolution = EvolutionAdapter(
        base_url=s.evolution_url,
        instance=s.evolution_instance,
        api_key=s.evolution_key,
    )
    router: SgpRouter | None = None
    try:
        async with task_session() as session:
            sgp_ond = await load_sgp_config(session, "ondeline")
            sgp_lnk = await load_sgp_config(session, "linknetam")
            router = SgpRouter(
                primary=SgpOndelineProvider(**sgp_ond),
                secondary=SgpLinkNetAMProvider(**sgp_lnk),
            )
            cache = SgpCacheService(
                redis=redis,
                session=session,
                router=router,
                ttl_cliente=s.sgp_cache_ttl_cliente,
                ttl_negativo=s.sgp_cache_ttl_negativo,
            )
            return await run_regua(
                session,
                evolution=evolution,
                sgp_cache=cache,
                redis=redis,
            )
    finally:
        if router is not None:
            await router.aclose()
        await evolution.aclose()


@celery_app.task(
    name="ondeline_api.workers.cobranca_jobs.run_regua_cobranca",
    bind=True,
)
def run_regua_cobranca(self: Any) -> dict[str, int]:
    try:
        result: dict[str, int] = cast(dict[str, int], run_task(_run))
        log.info("cobranca.regua.completed", **result)
        return result
    except Exception as e:
        log.error("cobranca.regua.failed", error=str(e), exc_info=True)
        raise
