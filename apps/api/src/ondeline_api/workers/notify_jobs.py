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
    broadcast_manutencao,
    lgpd_purge,
    schedule_atrasos,
    schedule_followup_os,
    schedule_pagamentos,
    schedule_vencimentos,
)
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.services.sgp_config import load_sgp_config
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import get_redis, reset_redis_cache, task_session

log = structlog.get_logger(__name__)


async def _run_planner() -> dict[str, int]:
    s = get_settings()
    redis = await get_redis()
    sgp_router: SgpRouter | None = None
    try:
        async with task_session() as session:
            sgp_ond = await load_sgp_config(session, "ondeline")
            sgp_lnk = await load_sgp_config(session, "linknetam")
            sgp_router = SgpRouter(
                primary=SgpOndelineProvider(**sgp_ond),
                secondary=SgpLinkNetAMProvider(**sgp_lnk),
            )
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
        if sgp_router is not None:
            await sgp_router.aclose()


def _run_in_thread_or_loop(coro_factory: Any) -> Any:
    """Same pattern as inbound/outbound — handle eager mode."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        from ondeline_api.db.engine import reset_engine_cache

        reset_engine_cache()
        reset_redis_cache()

        def _run_in_thread() -> Any:
            reset_engine_cache()
            reset_redis_cache()
            return asyncio.run(coro_factory())

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(_run_in_thread).result()
    return asyncio.run(coro_factory())


@celery_app.task(
    name="ondeline_api.workers.notify_jobs.run_planner_jobs",
    bind=True,
)
def run_planner_jobs(self: Any) -> dict[str, int]:
    """Beat-triggered: vencimentos + atrasos + pagamentos."""
    try:
        result: dict[str, int] = _run_in_thread_or_loop(_run_planner)
        log.info("planner_jobs.completed", **result)
        return result
    except Exception as e:
        log.error("planner_jobs.failed", error=str(e), exc_info=True)
        raise


async def _run_followup_os() -> int:
    async with task_session() as session:
        return await schedule_followup_os(session)


async def _run_manutencao() -> int:
    async with task_session() as session:
        return await broadcast_manutencao(session)


async def _run_lgpd() -> dict[str, int]:
    async with task_session() as session:
        return await lgpd_purge(session)


@celery_app.task(
    name="ondeline_api.workers.notify_jobs.followup_os_job",
    bind=True,
)
def followup_os_job(self: Any) -> int:
    try:
        result: int = _run_in_thread_or_loop(_run_followup_os)
        log.info("followup_os_job.completed", count=result)
        return result
    except Exception as e:
        log.error("followup_os_job.failed", error=str(e), exc_info=True)
        raise


@celery_app.task(
    name="ondeline_api.workers.notify_jobs.manutencao_job",
    bind=True,
)
def manutencao_job(self: Any) -> int:
    try:
        result: int = _run_in_thread_or_loop(_run_manutencao)
        log.info("manutencao_job.completed", count=result)
        return result
    except Exception as e:
        log.error("manutencao_job.failed", error=str(e), exc_info=True)
        raise


@celery_app.task(
    name="ondeline_api.workers.notify_jobs.lgpd_purge_job",
    bind=True,
)
def lgpd_purge_job(self: Any) -> dict[str, int]:
    try:
        result: dict[str, int] = _run_in_thread_or_loop(_run_lgpd)
        log.info("lgpd_purge_job.completed", **result)
        return result
    except Exception as e:
        log.error("lgpd_purge_job.failed", error=str(e), exc_info=True)
        raise
