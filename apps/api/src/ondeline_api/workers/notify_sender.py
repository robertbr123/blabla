"""Celery worker that processes the Notificacao queue."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.config import get_settings
from ondeline_api.db.models.business import Cliente
from ondeline_api.repositories.notificacao import NotificacaoRepo
from ondeline_api.services.notify_sender import send_one
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import run_task, task_session

log = structlog.get_logger(__name__)


async def _flush() -> dict[str, int]:
    s = get_settings()
    evolution = EvolutionAdapter(
        base_url=s.evolution_url,
        instance=s.evolution_instance,
        api_key=s.evolution_key,
    )
    sent = 0
    failed = 0
    try:
        async with task_session() as session:
            repo = NotificacaoRepo(session)
            due = await repo.list_due(now=datetime.now(tz=UTC), limit=100)
            for n in due:
                cliente = (
                    await session.execute(
                        select(Cliente).where(Cliente.id == n.cliente_id)
                    )
                ).scalar_one_or_none()
                if cliente is None or cliente.deleted_at is not None:
                    await repo.mark_failed(n)
                    failed += 1
                    continue
                ok = await send_one(session, evolution, n, cliente)
                if ok:
                    sent += 1
                else:
                    failed += 1
    finally:
        await evolution.aclose()
    return {"sent": sent, "failed": failed}




@celery_app.task(
    name="ondeline_api.workers.notify_sender.flush_pending",
    bind=True,
)
def flush_pending(self: Any) -> dict[str, int]:
    try:
        result: dict[str, int] = run_task(_flush)
        log.info("notify.flush.completed", **result)
        return result
    except Exception as e:
        log.error("notify.flush.failed", error=str(e), exc_info=True)
        raise
