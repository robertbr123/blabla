"""F7 — Tasks Celery na fila `asr`.

Fluxo:
  1. ``transcrever_audio_task(mensagem_id, conversa_id, message_key)`` baixa
     audio via Evolution, manda pra OpenAI Whisper, persiste transcricao.
  2. Se transcricao OK e nao vazia, dispara ``llm_turn_task`` pra que o LLM
     responda como se fosse mensagem de texto.

Mantemos fila separada (concurrency baixa) pra nao bloquear o worker LLM
em pico de audios.
"""
from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import structlog

from ondeline_api.adapters.asr.openai_whisper import OpenAiWhisperClient
from ondeline_api.config import get_settings
from ondeline_api.services.asr import transcrever_mensagem
from ondeline_api.services.canal_evolution import (
    evolution_for_instance,
    resolver_instance,
)
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import run_task, task_session

log = structlog.get_logger(__name__)


async def _run(
    mensagem_id: UUID,
    conversa_id: UUID,
    message_key: dict[str, Any] | None,
) -> dict[str, Any]:
    s = get_settings()
    if not s.openai_api_key:
        log.warning("asr.no_openai_key", conversa_id=str(conversa_id))
        return {"skipped": "no_openai_key"}

    asr = OpenAiWhisperClient(
        api_key=s.openai_api_key,
        url=s.openai_asr_url,
        model=s.openai_asr_model,
        language=s.openai_asr_language,
        timeout=s.openai_asr_timeout_seconds,
        max_bytes=s.openai_asr_max_bytes,
    )
    try:
        async with task_session() as session:
            instance = await resolver_instance(session, conversa_id, s)
            evolution = evolution_for_instance(instance, s)
            try:
                text = await transcrever_mensagem(
                    session,
                    mensagem_id,
                    asr=asr,
                    evolution=evolution,
                    external_message_key=message_key,
                )
            finally:
                await evolution.aclose()
    finally:
        await asr.aclose()

    if not text:
        return {"transcricao_status": "failed", "conversa_id": str(conversa_id)}

    # Encadeia turno do LLM pra que o bot responda ao texto transcrito.
    from ondeline_api.workers.llm_turn import llm_turn_task

    llm_turn_task.delay(conversa_id=str(conversa_id))

    return {
        "transcricao_status": "ok",
        "conversa_id": str(conversa_id),
        "chars": len(text),
    }


@celery_app.task(
    name="ondeline_api.workers.asr_jobs.transcrever_audio_task",
    bind=True,
    max_retries=1,
    default_retry_delay=10,
    queue="asr",
)
def transcrever_audio_task(
    self: Any,
    *,
    mensagem_id: str,
    conversa_id: str,
    message_key: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mid = UUID(mensagem_id)
    cid = UUID(conversa_id)
    try:
        return cast(
            dict[str, Any], run_task(lambda: _run(mid, cid, message_key))
        )
    except Exception as e:
        log.warning(
            "asr.task_error", conversa_id=conversa_id, error=str(e)
        )
        raise self.retry(exc=e) from e
