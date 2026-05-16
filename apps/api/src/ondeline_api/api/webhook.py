"""POST /webhook — entrada do Evolution.

Responsabilidades:
1. Body limit (defesa contra payloads gigantes)
2. (opcional) IP allowlist
3. HMAC X-Hub-Signature-256
4. Rate limit (slowapi + Redis)
5. Enfileira `process_inbound_message_task` no Celery
6. Retorna 202 Accepted imediatamente

Tudo o que envolve DB/LLM/Evolution acontece no worker.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from ondeline_api.config import get_settings
from ondeline_api.observability.metrics import (
    webhook_invalid_signature_total,
    webhook_received_total,
)
from ondeline_api.webhook.hmac import verify_signature
from ondeline_api.workers.inbound import process_inbound_message_task

log = structlog.get_logger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)


@router.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(lambda: get_settings().webhook_rate_limit)
async def evolution_webhook(
    request: Request,
) -> JSONResponse:
    settings = get_settings()
    webhook_received_total.inc()
    # Extract HMAC header manually — FastAPI's Header() with convert_underscores=False
    # looks for underscored names and misses the hyphenated HTTP header.
    x_hub_signature_256: str | None = request.headers.get("x-hub-signature-256")

    # 1) IP allowlist (opcional). When set, it doubles as an HMAC bypass: a
    # request coming from an allowlisted IP (typically a peer container on a
    # private docker network) skips signature verification. Evolution 2.x
    # does not sign webhooks natively, so this is the practical way to keep
    # the route secured without standing up a signing proxy.
    allow = settings.evolution_ip_allowlist_set()
    client_ip = request.client.host if request.client else ""
    ip_allowed = bool(allow) and client_ip in allow
    if allow and not ip_allowed:
        log.warning("webhook.ip_blocked", ip=client_ip)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ip not allowed")

    # 2) Body limit (Content-Length + leitura segura)
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

    # 3) HMAC — skipped when allowlisted IP or when no secret is configured.
    # Evolution API 2.x does not sign webhooks natively; leaving EVOLUTION_HMAC_SECRET
    # empty disables signature verification (rely on IP allowlist or network isolation).
    if (
        not ip_allowed
        and settings.evolution_hmac_secret
        and not verify_signature(body, x_hub_signature_256, settings.evolution_hmac_secret)
    ):
        webhook_invalid_signature_total.inc()
        log.warning("webhook.invalid_signature")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bad signature")

    # 4) Parse JSON
    import json

    try:
        payload = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid json") from e

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payload must be object")

    event = payload.get("event")
    if event != "messages.upsert":
        # ignora silenciosamente — Evolution dispara muitos eventos (presence, status, etc)
        return JSONResponse({"status": "ignored", "event": event}, status_code=status.HTTP_200_OK)

    # 5) Enfileira
    process_inbound_message_task.delay(payload)
    return JSONResponse({"status": "accepted"}, status_code=status.HTTP_202_ACCEPTED)
