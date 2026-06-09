"""Task Celery: baixa e persiste midia inbound (foto/audio/video/doc do cliente).

Roda na fila ``default``. Espelha o padrao do ASR: recebe ``mensagem_id`` +
``message_key`` provider-especifico (Cloud: ``{media_id}``; Evolution:
``{id, remoteJid, fromMe}``) e baixa via ``adapter_for_conversa``.

Disparado logo apos o webhook pra que a URL temporaria do Meta (~5min) ainda
seja valida. Idempotente: nao rebaixa se o arquivo ja existe em disco.
"""
from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import structlog

from ondeline_api.config import get_settings
from ondeline_api.services.conversa_media import download_and_store
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import run_task, task_session

log = structlog.get_logger(__name__)


async def _run(
    mensagem_id: UUID,
    conversa_id: UUID,
    message_key: dict[str, Any] | None,
) -> dict[str, Any]:
    s = get_settings()
    async with task_session() as session:
        path = await download_and_store(
            session, mensagem_id, message_key=message_key, settings=s
        )
    return {"stored": bool(path), "conversa_id": str(conversa_id)}


@celery_app.task(
    name="ondeline_api.workers.media_jobs.baixar_midia_task",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
    queue="default",
)
def baixar_midia_task(
    self: Any,
    *,
    mensagem_id: str,
    conversa_id: str,
    message_key: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mid = UUID(mensagem_id)
    cid = UUID(conversa_id)
    try:
        return cast(dict[str, Any], run_task(lambda: _run(mid, cid, message_key)))
    except Exception as e:
        log.warning("media.task_error", conversa_id=conversa_id, error=str(e))
        raise self.retry(exc=e) from e
