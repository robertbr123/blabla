# apps/api/src/ondeline_api/services/broadcast_sender.py
"""Envio de mensagens de campanha (broadcast) — uma por destinatário.

Usa as mesmas primitivas do notify_sender (send_template + record_sent), mas é
isolado do pipeline de notificações transacionais.
"""
from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.whatsapp import WhatsAppAdapter, WhatsAppError
from ondeline_api.db.models.business import Campanha, CampanhaDestinatario
from ondeline_api.services.whatsapp_message_log import extract_wamid, record_sent

log = structlog.get_logger(__name__)


def _merge_params(defaults: list[str] | None, overrides: list[str] | None) -> list[str]:
    """Mescla params por contato com os padrões da campanha.

    Usa o override quando presente e não-vazio; senão o default na mesma posição.
    """
    base = list(defaults or [])
    if not overrides:
        return base
    n = max(len(base), len(overrides))
    out: list[str] = []
    for i in range(n):
        ov = overrides[i] if i < len(overrides) else None
        if ov is not None and ov != "":
            out.append(ov)
        else:
            out.append(base[i] if i < len(base) else "")
    return out


async def enviar_destinatario(
    session: AsyncSession,
    adapter: WhatsAppAdapter,
    campanha: Campanha,
    destinatario: CampanhaDestinatario,
) -> bool:
    """Envia o template da campanha para 1 destinatário. Atualiza o status dele.

    Returns True se enviado, False se falhou.
    """
    body_params = _merge_params(campanha.body_params, destinatario.body_params)
    button_param = destinatario.button_param or campanha.button_param
    try:
        send_result = await adapter.send_template(
            destinatario.whatsapp,
            name=campanha.template_name,
            language=campanha.template_language,
            body_params=body_params,
            header_media_url=campanha.header_media_url,
            button_url_param=button_param,
        )
    except WhatsAppError as e:
        destinatario.status = "falha"
        destinatario.erro = str(e)[:500]
        log.warning("broadcast.send_failed", dest_id=str(destinatario.id), error=str(e))
        return False
    except NotImplementedError:
        destinatario.status = "falha"
        destinatario.erro = "canal não suporta template (provider != cloud)"
        return False

    wamid = extract_wamid(send_result)
    destinatario.status = "enviada"
    destinatario.wamid = wamid
    destinatario.enviada_em = datetime.now(tz=UTC)
    await record_sent(
        session,
        wamid=wamid,
        template_name=campanha.template_name,
        recipient_jid=destinatario.whatsapp,
    )
    return True


# status Meta -> status do destinatário
_STATUS_MAP = {"delivered": "entregue", "read": "lida", "failed": "falha"}


async def atualizar_status_por_wamid(
    session: AsyncSession, *, wamid: str, status_meta: str
) -> None:
    """Atualiza o destinatário (se existir) a partir de um status do webhook Cloud.

    Fail-open: erro de DB não propaga. Não "rebaixa" status (read não vira
    delivered) — só aplica delivered->entregue, read->lida, failed->falha.
    """
    novo = _STATUS_MAP.get(status_meta)
    if not novo or not wamid:
        return
    try:
        stmt = (
            update(CampanhaDestinatario)
            .where(
                CampanhaDestinatario.wamid == wamid,
                # nunca rebaixa: 'lida' é terminal, ignora delivered/failed atrasados
                CampanhaDestinatario.status != "lida",
            )
            .values(status=novo)
        )
        await session.execute(stmt)
    except Exception as e:
        log.warning("broadcast.status_update_failed", wamid=wamid, error=str(e))
