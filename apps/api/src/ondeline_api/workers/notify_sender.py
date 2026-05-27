"""Celery worker that processes the Notificacao queue.

Provider-aware: resolve o canal de cada notificacao via a conversa ativa do
cliente (cache em memoria pro batch). Se nao houver conversa, cai no canal
default (settings.evolution_instance, provider=evolution).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select

from ondeline_api.adapters.whatsapp import WhatsAppAdapter, build_for_canal
from ondeline_api.config import get_settings
from ondeline_api.db.models.business import Canal, Cliente, Conversa
from ondeline_api.repositories.notificacao import NotificacaoRepo
from ondeline_api.services.canal_whatsapp import build_for_instance  # type: ignore[attr-defined]
from ondeline_api.services.notify_sender import send_one
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import run_task, task_session

log = structlog.get_logger(__name__)


async def _flush() -> dict[str, int]:
    s = get_settings()
    sent = 0
    failed = 0

    # Cache de adapters por canal_id (None = default). Cada adapter abre seu
    # proprio http client, entao queremos reusar dentro do batch.
    adapter_cache: dict[UUID | None, WhatsAppAdapter] = {}
    canal_cache: dict[UUID, Canal] = {}

    async def adapter_for_cliente(session: Any, cliente_id: UUID) -> WhatsAppAdapter:
        # Pega o canal_id da conversa mais recente do cliente.
        stmt = (
            select(Conversa.canal_id)
            .where(Conversa.cliente_id == cliente_id)
            .order_by(Conversa.created_at.desc())
            .limit(1)
        )
        canal_id = (await session.execute(stmt)).scalar_one_or_none()

        if canal_id in adapter_cache:
            return adapter_cache[canal_id]

        if canal_id is None:
            adapter = build_for_instance(s.evolution_instance, s)
        else:
            canal = canal_cache.get(canal_id)
            if canal is None:
                canal = (
                    await session.execute(
                        select(Canal).where(Canal.id == canal_id)
                    )
                ).scalar_one_or_none()
                if canal is not None:
                    canal_cache[canal_id] = canal
            if canal is None:
                # Conversa aponta pra canal removido — falha-aberta.
                adapter = build_for_instance(s.evolution_instance, s)
            else:
                adapter = build_for_canal(canal, s)

        adapter_cache[canal_id] = adapter
        return adapter

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
                adapter = await adapter_for_cliente(session, cliente.id)
                ok = await send_one(session, adapter, n, cliente)
                if ok:
                    sent += 1
                else:
                    failed += 1
    finally:
        # Fecha todos os http clients abertos no batch.
        for adapter in adapter_cache.values():
            try:
                await adapter.aclose()
            except Exception as e:
                log.warning("notify.adapter_close_failed", error=str(e))
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
