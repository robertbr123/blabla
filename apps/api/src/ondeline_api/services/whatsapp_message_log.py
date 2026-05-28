"""Persiste eventos do ciclo de vida de mensagens outbound Cloud.

Fase 2.2 do plano de evolucao. Duas operacoes:

- ``record_sent`` — chamado logo apos ``adapter.send_template`` (ou
  ``send_text``) retornar com sucesso. Captura ``wamid`` do retorno do Meta
  e grava na tabela ``whatsapp_message_status``.
- ``record_status_update`` — chamado pelo handler do webhook Cloud quando
  chega ``sent`` / ``delivered`` / ``read`` / ``failed``. Faz UPDATE no row
  do wamid correspondente.

Falha-aberta: erros aqui nao quebram o envio nem o webhook — apenas logam.
Metricas perdem precisao mas o fluxo principal continua.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import WhatsAppMessageStatus

log = structlog.get_logger(__name__)


def extract_wamid(send_result: dict[str, Any] | None) -> str | None:
    """Extrai ``messages[0].id`` (wamid) da resposta da Cloud API.

    Estrutura tipica: ``{"messages": [{"id": "wamid.HBgM..."}]}``.
    Retorna None se ``send_result`` for ``None``, vazio, ou nao tem ``messages``.
    Tolerante a estrutura de Evolution (que NAO retorna wamid) — None nesse caso.
    """
    if not send_result:
        return None
    msgs = send_result.get("messages")
    if not isinstance(msgs, list) or not msgs:
        return None
    first = msgs[0]
    if not isinstance(first, dict):
        return None
    wamid = first.get("id")
    return str(wamid) if wamid else None


async def record_sent(
    session: AsyncSession,
    *,
    wamid: str | None,
    template_name: str | None,
    recipient_jid: str,
) -> None:
    """Grava o envio. Idempotente: se wamid ja existe, ignora (ON CONFLICT)."""
    if not wamid:
        return  # Evolution / nao-Cloud nao tem wamid; ignora silenciosamente.
    try:
        stmt = (
            pg_insert(WhatsAppMessageStatus)
            .values(
                wamid=wamid,
                template_name=template_name,
                recipient_jid=recipient_jid,
            )
            .on_conflict_do_nothing(index_elements=["wamid"])
        )
        await session.execute(stmt)
    except Exception as e:
        log.warning(
            "whatsapp_log.record_sent_failed",
            wamid=wamid,
            template=template_name,
            error=str(e),
        )


async def record_status_update(
    session: AsyncSession,
    *,
    wamid: str,
    status: str,
    timestamp_unix: str | None = None,
    error: list[dict[str, Any]] | None = None,
) -> None:
    """Atualiza o timestamp correspondente ao status recebido.

    ``status`` esperado: ``sent`` | ``delivered`` | ``read`` | ``failed``.
    ``timestamp_unix`` e a string unix epoch que o Meta manda; convertida pra
    datetime UTC. Se faltando ou invalida, usa ``now()``.
    """
    ts = _parse_meta_timestamp(timestamp_unix)
    values: dict[str, Any] = {}
    if status == "sent":
        # Ja gravamos sent_at no record_sent; este UPDATE so confirma idempotencia
        # se o webhook chegar antes do record_sent (raro mas possivel com
        # eventual consistency). Sem alterar sent_at pra nao mascarar o real.
        return
    elif status == "delivered":
        values["delivered_at"] = ts
    elif status == "read":
        values["read_at"] = ts
    elif status == "failed":
        values["failed_at"] = ts
        if error:
            values["error"] = error
    else:
        return  # status desconhecido — ignora

    try:
        stmt = (
            update(WhatsAppMessageStatus)
            .where(WhatsAppMessageStatus.wamid == wamid)
            .values(**values)
        )
        await session.execute(stmt)
    except Exception as e:
        log.warning(
            "whatsapp_log.record_status_failed",
            wamid=wamid,
            status=status,
            error=str(e),
        )


def _parse_meta_timestamp(raw: str | None) -> datetime:
    """Meta manda timestamp como string unix epoch (segundos). UTC."""
    if not raw:
        return datetime.now(UTC)
    try:
        return datetime.fromtimestamp(int(raw), tz=UTC)
    except (ValueError, TypeError):
        return datetime.now(UTC)
