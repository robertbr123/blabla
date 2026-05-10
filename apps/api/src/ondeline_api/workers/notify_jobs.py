"""Notification planner Celery jobs (Beat-triggered)."""
from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any

import structlog

from ondeline_api.adapters.sgp.linknetam import SgpLinkNetAMProvider
from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.config import get_settings
from ondeline_api.services.notify_planner import (
    schedule_atrasos,
    schedule_pagamentos,
    schedule_vencimentos,
)
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import get_redis, task_session

log = structlog.get_logger(__name__)


async def _run_planner() -> dict[str, int]:
    s = get_settings()
    redis = await get_redis()
    sgp_router = SgpRouter(
        primary=SgpOndelineProvider(
            base_url=s.sgp_ondeline_base, token=s.sgp_ondeline_token, app=s.sgp_ondeline_app
        ),
        secondary=SgpLinkNetAMProvider(
            base_url=s.sgp_linknetam_base, token=s.sgp_linknetam_token, app=s.sgp_linknetam_app
        ),
    )
    try:
        async with task_session() as session:
            cache = SgpCacheService(
                redis=redis,
                session=session,
                router=sgp_router,
                ttl_cliente=s.sgp_cache_ttl_cliente,
                ttl_negativo=s.sgp_cache_ttl_negativo,
            )
            v = await schedule_vencimentos(session, cache)
            a = await schedule_atrasos(session, cache)
            p = await schedule_pagamentos(session, cache)
        return {"vencimentos": v, "atrasos": a, "pagamentos": p}
    finally:
        await sgp_router.aclose()


def _run_in_thread_or_loop(coro_factory: Any) -> dict[str, int]:
    """Same pattern as inbound/outbound — handle eager mode."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        from ondeline_api.db.engine import reset_engine_cache

        reset_engine_cache()

        def _run_in_thread() -> dict[str, int]:
            reset_engine_cache()
            result: dict[str, int] = asyncio.run(coro_factory())
            return result

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(_run_in_thread).result()
    result: dict[str, int] = asyncio.run(coro_factory())
    return result


@celery_app.task(
    name="ondeline_api.workers.notify_jobs.run_planner_jobs",
    bind=True,
)
def run_planner_jobs(self: Any) -> dict[str, int]:
    """Beat-triggered: vencimentos + atrasos + pagamentos."""
    try:
        result = _run_in_thread_or_loop(_run_planner)
        log.info("planner_jobs.completed", **result)
        return result
    except Exception as e:
        log.error("planner_jobs.failed", error=str(e), exc_info=True)
        raise
