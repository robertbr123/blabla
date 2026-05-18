"""Task Celery: gera resumo do handoff bot->humano em fila `llm`."""
from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import structlog

from ondeline_api.adapters.llm.hermes import HermesProvider
from ondeline_api.config import get_settings
from ondeline_api.services.handoff_summary import gerar_resumo_handoff
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import run_task, task_session

log = structlog.get_logger(__name__)


async def _run(conversa_id: UUID) -> dict[str, Any]:
    s = get_settings()
    llm_url, llm_key, llm_model = s.effective_llm()
    provider = HermesProvider(
        base_url=llm_url,
        model=llm_model,
        api_key=llm_key,
        timeout=s.llm_timeout_seconds,
    )
    try:
        async with task_session() as session:
            resumo = await gerar_resumo_handoff(
                session, conversa_id, provider, model=llm_model
            )
        return {
            "conversa_id": str(conversa_id),
            "generated": resumo is not None,
            "chars": len(resumo) if resumo else 0,
        }
    finally:
        await provider.aclose()


@celery_app.task(
    name="ondeline_api.workers.handoff_summary_task.handoff_summary_task",
    bind=True,
    max_retries=1,
    default_retry_delay=15,
    queue="llm",
)
def handoff_summary_task(self: Any, *, conversa_id: str) -> dict[str, Any]:
    cid = UUID(conversa_id)
    try:
        return cast(dict[str, Any], run_task(lambda: _run(cid)))
    except Exception as e:
        # Falha de LLM ja e capturada dentro do servico; aqui retentamos so erro de infra.
        log.warning("handoff_summary_task.error", conversa_id=conversa_id, error=str(e))
        raise self.retry(exc=e) from e
