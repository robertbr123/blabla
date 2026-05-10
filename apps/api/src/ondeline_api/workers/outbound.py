"""Task Celery: envia mensagem do bot para Evolution + persiste em Mensagem(role=BOT)."""
from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any
from uuid import UUID

import structlog

from ondeline_api.adapters.evolution import EvolutionAdapter, EvolutionError
from ondeline_api.config import get_settings
from ondeline_api.observability.metrics import (
    evolution_send_failure_total,
    evolution_send_total,
)
from ondeline_api.repositories.mensagem import MensagemRepo
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import task_session

log = structlog.get_logger(__name__)


async def _run(jid: str, text: str, conversa_id: UUID) -> dict[str, str]:
    settings = get_settings()
    adapter = EvolutionAdapter(
        base_url=settings.evolution_url,
        instance=settings.evolution_instance,
        api_key=settings.evolution_key,
    )
    try:
        result = await adapter.send_text(jid, text)
        evolution_send_total.inc()
    except EvolutionError as e:
        evolution_send_failure_total.inc()
        log.error("outbound.send_failed", jid=jid, error=str(e))
        raise
    finally:
        await adapter.aclose()

    async with task_session() as session:
        await MensagemRepo(session).insert_bot_reply(conversa_id=conversa_id, text=text)

    log.info(
        "outbound.sent",
        jid=jid,
        conversa_id=str(conversa_id),
        evolution_msg_id=(result.get("key") or {}).get("id"),
    )
    return {"status": "ok"}


@celery_app.task(
    name="ondeline_api.workers.outbound.send_outbound_task",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def send_outbound_task(
    self: Any, *, jid: str, text: str, conversa_id: str
) -> dict[str, str]:
    try:
        # asyncio.run() cannot be called from a running event loop (e.g. when the
        # task fires eagerly inside Starlette's TestClient or from another task
        # thread).  Detect and run in a dedicated thread to get a fresh loop.
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            # Reset engine cache before spawning thread so the thread creates its
            # own asyncpg pool bound to its event loop (pools are per-loop).
            from ondeline_api.db.engine import reset_engine_cache

            def _run_in_thread(j: str, t: str, c: UUID) -> dict[str, str]:
                reset_engine_cache()
                return asyncio.run(_run(j, t, c))

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(_run_in_thread, jid, text, UUID(conversa_id)).result()
        return asyncio.run(_run(jid, text, UUID(conversa_id)))
    except Exception as e:
        raise self.retry(exc=e) from e
