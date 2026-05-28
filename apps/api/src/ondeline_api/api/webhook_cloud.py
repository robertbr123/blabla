"""GET/POST /webhook/whatsapp-cloud — entrada da Cloud API (Meta).

Diferencas vs ``/webhook`` (Evolution):
- **GET**: handshake do Meta. Valida ``hub.verify_token`` contra
  ``settings.whatsapp_cloud_verify_token`` e devolve ``hub.challenge`` cru.
  Sem isso o Meta nao registra o webhook.
- **POST**: HMAC obrigatorio (Meta sempre assina) usando
  ``settings.whatsapp_cloud_app_secret``. Sem allowlist de IP — Meta usa
  faixa de IPs ampla que muda; o HMAC e nossa unica defesa.

Eventos que nao sao ``messages`` (ex: ``statuses`` de delivered/read) sao
respondidos com 200 OK + ``{"status":"ignored"}`` pra evitar retries do Meta.
"""
from __future__ import annotations

import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.config import get_settings
from ondeline_api.deps import get_db
from ondeline_api.observability.metrics import (
    webhook_invalid_signature_total,
    webhook_received_total,
)
from ondeline_api.services.whatsapp_message_log import record_status_update
from ondeline_api.webhook.hmac import verify_signature
from ondeline_api.webhook.parser_cloud import (
    iter_cloud_messages,
    iter_cloud_statuses,
)
from ondeline_api.workers.inbound import process_inbound_message_task

log = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/webhook/whatsapp-cloud")
async def whatsapp_cloud_verify(request: Request) -> PlainTextResponse:
    """Handshake do Meta. Tem que devolver o ``hub.challenge`` cru (text/plain)."""
    settings = get_settings()
    qp = request.query_params
    mode = qp.get("hub.mode")
    token = qp.get("hub.verify_token")
    challenge = qp.get("hub.challenge")

    expected = settings.whatsapp_cloud_verify_token
    if mode == "subscribe" and expected and token == expected and challenge:
        return PlainTextResponse(challenge, status_code=status.HTTP_200_OK)

    log.warning(
        "webhook_cloud.verify_failed", mode=mode, has_token=bool(token), has_expected=bool(expected)
    )
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="verify failed")


@router.post("/webhook/whatsapp-cloud", status_code=status.HTTP_202_ACCEPTED)
async def whatsapp_cloud_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> JSONResponse:
    settings = get_settings()
    webhook_received_total.inc()

    # 1) Body limit
    cl = request.headers.get("content-length")
    if cl and int(cl) > settings.webhook_max_body_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="payload too large",
        )
    body = await request.body()
    if len(body) > settings.webhook_max_body_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="payload too large",
        )

    # 2) HMAC (Meta assina com app_secret). Sem secret configurado = recusa tudo
    # — caminho do Meta nunca deve rodar sem app_secret. Diferente da Evolution
    # onde a falta de secret = bypass (Evolution 2.x nao assina nativamente).
    secret = settings.whatsapp_cloud_app_secret
    sig = request.headers.get("x-hub-signature-256")
    if not secret:
        log.warning("webhook_cloud.app_secret_missing")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="cloud webhook not configured",
        )
    if not verify_signature(body, sig, secret):
        webhook_invalid_signature_total.inc()
        log.warning("webhook_cloud.invalid_signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="bad signature"
        )

    # 3) Parse JSON
    try:
        payload = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid json"
        ) from e
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="payload must be object"
        )

    # 4) Status updates (delivered/read/failed/sent) — apenas log, nao
    # enfileira pra processamento. Ajuda a debugar entrega de midia em
    # sandbox e identificar falhas de entrega em producao.
    try:
        statuses = iter_cloud_statuses(payload)
    except Exception as e:
        log.warning("webhook_cloud.statuses_parse_error", error=str(e))
        statuses = []
    for st in statuses:
        if st["status"] == "failed":
            log.warning(
                "webhook_cloud.message_failed",
                msg_id=st["id"],
                recipient=st["recipient_id"],
                errors=st["errors"],
            )
        else:
            log.info(
                "webhook_cloud.message_status",
                msg_id=st["id"],
                status=st["status"],
                recipient=st["recipient_id"],
            )
        # Persiste atualizacao no whatsapp_message_status (Fase 2.2).
        # Falha-aberta: erro de DB nao quebra o webhook (Meta retentaria).
        if st["id"]:
            await record_status_update(
                session,
                wamid=st["id"],
                status=st["status"],
                timestamp_unix=st.get("timestamp"),
                error=st.get("errors") if st["status"] == "failed" else None,
            )
    if statuses:
        await session.commit()

    # 5) Extrai messages inbound
    try:
        events = iter_cloud_messages(payload)
    except Exception as e:
        log.warning("webhook_cloud.parse_error", error=str(e))
        return JSONResponse(
            {"status": "ignored", "reason": "parse_error"},
            status_code=status.HTTP_200_OK,
        )

    if not events:
        # Sem messages — pode ter sido so status update (ja logado acima)
        return JSONResponse(
            {"status": "ignored", "reason": "no_messages", "statuses": len(statuses)},
            status_code=status.HTTP_200_OK,
        )

    # 5) Enfileira cada mensagem. Reutiliza o mesmo task da Evolution mas com
    # payload "encapsulado" pra que o worker reconheca como Cloud — passamos
    # o dict cru pra inbound.process_inbound_message_task e o worker decide
    # qual parser usar baseado em ``object`` no payload.
    for _evt in events:
        # Worker espera o payload cru pra fazer dedup + auditoria. Mandamos o
        # payload inteiro pra cada mensagem (na pratica vem 1 por payload).
        process_inbound_message_task.delay(payload)
        break  # so 1 dispatch por payload — worker itera as messages internamente

    return JSONResponse({"status": "accepted", "count": len(events)})
