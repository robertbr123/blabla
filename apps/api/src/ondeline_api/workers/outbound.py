"""Task Celery: envia mensagem do bot via adapter provider-aware + persiste Mensagem(role=BOT).

Resolve o canal da conversa (Evolution ou Cloud) e usa o WhatsAppAdapter
correto. Caminho Evolution preservado: ``adapter_for_conversa`` devolve
EvolutionAdapter quando ``canal.provider='evolution'``.
"""
from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import structlog

from ondeline_api.adapters.whatsapp import WhatsAppError
from ondeline_api.config import get_settings
from ondeline_api.observability.metrics import (
    evolution_send_failure_total,
    evolution_send_total,
)
from ondeline_api.repositories.mensagem import MensagemRepo
from ondeline_api.services.canal_whatsapp import adapter_for_conversa
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import get_redis, run_task, task_session

log = structlog.get_logger(__name__)


async def _run(
    jid: str, text: str, conversa_id: UUID, idempotency_key: str | None = None
) -> dict[str, str]:
    settings = get_settings()
    redis = await get_redis()

    # Idempotência: a task é acks_late e envia o WhatsApp ANTES do commit. Se ela
    # re-tentar (falha no insert/commit — gatilho realista), reenviaria a mesma
    # mensagem. Guard por task_id (estável entre retries): marca `outbound:sent`
    # logo após o envio; no retry, pula o envio mas refaz o insert (idempotente).
    sent_key = f"outbound:sent:{idempotency_key}" if idempotency_key else None
    already_sent = False
    if sent_key is not None:
        try:
            already_sent = bool(await redis.get(sent_key))
        except Exception:
            already_sent = False

    result: dict[str, Any] | None = None
    adapter_name = "skipped"
    async with task_session() as session:
        if not already_sent:
            # F4 + Cloud: devolve EvolutionAdapter OU CloudAdapter conforme
            # canal.provider da conversa. Fallback pro Evolution default se
            # conversa sem canal_id (legado).
            adapter = await adapter_for_conversa(session, conversa_id, settings)
            adapter_name = type(adapter).__name__
            try:
                result = await adapter.send_text(jid, text)
                evolution_send_total.inc()
                if sent_key is not None:
                    try:
                        await redis.set(sent_key, "1", ex=3600)
                    except Exception:
                        pass
            except WhatsAppError as e:
                evolution_send_failure_total.inc()
                log.error(
                    "outbound.send_failed", jid=jid, error=str(e),
                    adapter=adapter_name,
                )
                raise
            finally:
                await adapter.aclose()
        await MensagemRepo(session).insert_bot_reply(conversa_id=conversa_id, text=text)

    try:
        import datetime

        from ondeline_api.services.conversa_events import publish as _pub

        await _pub(
            redis,
            conversa_id,
            {
                "type": "msg",
                "role": "bot",
                "text": text,
                "ts": datetime.datetime.now(tz=datetime.UTC).isoformat(),
            },
        )
    except Exception:
        pass

    # msg_id pode vir de 2 shapes diferentes (None se o envio foi pulado por
    # idempotência):
    # - Evolution: result["key"]["id"]
    # - Cloud API: result["messages"][0]["id"]
    msg_id: str | None = None
    if result is not None:
        if isinstance(result.get("key"), dict):
            msg_id = result["key"].get("id")
        elif isinstance(result.get("messages"), list) and result["messages"]:
            first = result["messages"][0]
            if isinstance(first, dict):
                msg_id = first.get("id")

    log.info(
        "outbound.sent",
        jid=jid,
        conversa_id=str(conversa_id),
        msg_id=msg_id,
        adapter=adapter_name,
        skipped_send=already_sent,
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
    cid = UUID(conversa_id)
    # self.request.id é o task_id do Celery — estável entre re-tentativas, então
    # serve de chave de idempotência pra não reenviar a mesma mensagem.
    idem = self.request.id
    try:
        return cast(dict[str, str], run_task(lambda: _run(jid, text, cid, idem)))
    except Exception as e:
        raise self.retry(exc=e) from e
