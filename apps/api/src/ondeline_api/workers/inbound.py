"""Task Celery: processa mensagem entrante do webhook.

Recebe o payload bruto da Evolution (dict JSON-serializavel), parseia,
abre sessao, instancia repositorios + outbound enqueuer, e delega ao service.
Retorna dict com o resultado para fins de telemetria/debug.
"""
from __future__ import annotations

from typing import Any, cast

import structlog

from ondeline_api.config import get_settings
from ondeline_api.observability.metrics import (
    msgs_dedup_total,
    msgs_processed_total,
)
from ondeline_api.repositories.conversa import ConversaRepo
from ondeline_api.repositories.mensagem import MensagemRepo
from ondeline_api.services.inbound import (
    InboundDeps,
    InboundResult,
    process_inbound_message,
)
from ondeline_api.webhook.parser import ParseError, parse_messages_upsert
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import (
    BufferedOutboundEnqueuer,
    get_redis,
    run_task,
    task_session,
)

log = structlog.get_logger(__name__)


async def _run(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        evt = parse_messages_upsert(payload)
    except ParseError as e:
        log.warning("inbound.parse_error", error=str(e))
        return {"skipped": "parse_error", "error": str(e)}

    settings = get_settings()
    # BufferedOutboundEnqueuer coleta os sends durante a sessao; faz flush APOS
    # o commit para que as tasks outbound vejam os dados ja commitados.
    # Em modo eager (task_always_eager), o flush executaria send_outbound_task
    # sincronamente antes do commit se usassemos CeleryOutboundEnqueuer direto.
    outbound_buf = BufferedOutboundEnqueuer()
    redis = await get_redis()
    async with task_session() as session:
        deps = InboundDeps(
            conversas=ConversaRepo(session),
            mensagens=MensagemRepo(session),
            outbound=outbound_buf,
            ack_text=settings.bot_ack_text,
            redis=redis,
            session=session,
        )
        result: InboundResult = await process_inbound_message(evt, deps)
    # Session committed — safe to dispatch outbound tasks now.
    outbound_buf.flush()

    if result.duplicate:
        msgs_dedup_total.inc()
    elif result.persisted:
        msgs_processed_total.inc()

    log.info(
        "inbound.processed",
        external_id=evt.external_id,
        jid=evt.jid,
        kind=evt.kind.value,
        persisted=result.persisted,
        duplicate=result.duplicate,
        escalated=result.escalated,
        skipped=result.skipped_reason,
    )
    return {
        "conversa_id": str(result.conversa_id) if result.conversa_id else None,
        "persisted": result.persisted,
        "duplicate": result.duplicate,
        "escalated": result.escalated,
        "skipped_reason": result.skipped_reason,
    }


@celery_app.task(
    name="ondeline_api.workers.inbound.process_inbound_message_task",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def process_inbound_message_task(self: Any, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return cast(dict[str, Any], run_task(lambda: _run(payload)))
    except Exception as e:  # pragma: no cover — caminho de retry
        log.error("inbound.task_failed", error=str(e), exc_info=True)
        raise self.retry(exc=e) from e
