# apps/api/src/ondeline_api/workers/broadcast.py
"""Celery task de disparo em massa (comunicados).

Materializa os destinatários do segmento (idempotente), envia o template em
lotes respeitando o ritmo configurado, e atualiza contadores/status.
"""
from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select

from ondeline_api.adapters.whatsapp import build_for_canal
from ondeline_api.config import get_settings
from ondeline_api.db.models.business import (
    Campanha,
    CampanhaDestinatario,
    Canal,
)
from ondeline_api.services.broadcast_sender import enviar_destinatario
from ondeline_api.services.segmento import resolver_segmento
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import run_task, task_session

log = structlog.get_logger(__name__)


async def _materializar_destinatarios(session: Any, campanha: Campanha) -> int:
    """Cria as linhas de destinatário se ainda não existirem. Idempotente."""
    existing = (
        await session.execute(
            select(CampanhaDestinatario.id)
            .where(CampanhaDestinatario.campanha_id == campanha.id)
            .limit(1)
        )
    ).first()
    if existing is not None:
        return campanha.total_destinatarios

    clientes = list(
        (await session.execute(resolver_segmento(campanha.segmentacao))).scalars().all()
    )
    for c in clientes:
        session.add(
            CampanhaDestinatario(
                campanha_id=campanha.id,
                cliente_id=c.id,
                whatsapp=c.whatsapp,
                status="pendente",
            )
        )
    campanha.total_destinatarios = len(clientes)
    await session.flush()
    return len(clientes)


async def _send_campanha(session: Any, campanha_id: UUID) -> dict[str, int]:
    s = get_settings()
    campanha = (
        await session.execute(select(Campanha).where(Campanha.id == campanha_id))
    ).scalar_one_or_none()
    if campanha is None:
        return {"enviadas": 0, "falhas": 0}
    if campanha.status in {"concluida", "cancelada"}:
        return {"enviadas": campanha.enviadas, "falhas": campanha.falhas}

    canal = (
        await session.execute(select(Canal).where(Canal.id == campanha.canal_id))
    ).scalar_one_or_none()
    if canal is None or canal.provider != "cloud":
        campanha.status = "erro"
        await session.commit()
        return {"enviadas": 0, "falhas": 0}

    from datetime import UTC, datetime

    campanha.status = "enviando"
    if campanha.started_at is None:
        campanha.started_at = datetime.now(tz=UTC)
    await _materializar_destinatarios(session, campanha)
    await session.commit()

    adapter = build_for_canal(canal, s)
    enviadas = campanha.enviadas
    falhas = campanha.falhas
    try:
        while True:
            pendentes = list(
                (
                    await session.execute(
                        select(CampanhaDestinatario)
                        .where(
                            CampanhaDestinatario.campanha_id == campanha.id,
                            CampanhaDestinatario.status == "pendente",
                        )
                        .limit(s.broadcast_batch_size)
                    )
                )
                .scalars()
                .all()
            )
            if not pendentes:
                break
            for dest in pendentes:
                ok = await enviar_destinatario(session, adapter, campanha, dest)
                if ok:
                    enviadas += 1
                else:
                    falhas += 1
            campanha.enviadas = enviadas
            campanha.falhas = falhas
            await session.commit()
            await asyncio.sleep(s.broadcast_pause_seconds)
    finally:
        try:
            await adapter.aclose()
        except Exception as e:
            log.warning("broadcast.adapter_close_failed", error=str(e))

    campanha.status = "concluida"
    campanha.finished_at = datetime.now(tz=UTC)
    await session.commit()
    log.info("broadcast.done", campanha_id=str(campanha.id), enviadas=enviadas, falhas=falhas)
    return {"enviadas": enviadas, "falhas": falhas}


@celery_app.task(name="ondeline_api.workers.broadcast.send_campanha_task", bind=True)
def send_campanha_task(self: Any, campanha_id: str) -> dict[str, int]:
    async def _run() -> dict[str, int]:
        async with task_session() as session:
            return await _send_campanha(session, UUID(campanha_id))

    try:
        result: dict[str, int] = run_task(_run)
        log.info("broadcast.task.completed", campanha_id=campanha_id, **result)
        return result
    except Exception as e:
        log.error("broadcast.task.failed", campanha_id=campanha_id, error=str(e), exc_info=True)
        raise
