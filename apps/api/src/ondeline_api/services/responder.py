"""Service: atendente responde mensagem na conversa.

Persiste Mensagem(role=ATENDENTE) e enfileira envio outbound via Celery.
Reusa BufferedOutboundEnqueuer para envio pos-commit.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.crypto import encrypt_pii
from ondeline_api.db.models.business import Mensagem, MensagemRole
from ondeline_api.db.models.identity import User
from ondeline_api.repositories.conversa import ConversaRepo
from ondeline_api.services.conversa_events import publish as publish_event


class _OutboundEnqueuer(Protocol):
    def enqueue_send_outbound(
        self, jid: str, text: str, conversa_id: UUID, *, persist: bool = True
    ) -> None: ...


def _assinatura(nome: str | None) -> str:
    """Nome que assina a mensagem no WhatsApp. Sem nome cadastrado: SUPORTE.

    Tira `*` e `_` (marcadores de formatacao do WhatsApp) pra nao quebrar o negrito.
    """
    limpo = " ".join((nome or "").replace("*", "").replace("_", " ").split())
    return limpo or "SUPORTE"


async def responder(
    session: AsyncSession,
    conversa_id: UUID,
    atendente_id: UUID,
    text: str,
    enqueuer: _OutboundEnqueuer,
    redis: aioredis.Redis[bytes] | None = None,
) -> Mensagem:
    repo = ConversaRepo(session)
    c = await repo.get_by_id(conversa_id)
    if c is None:
        raise LookupError(str(conversa_id))

    if c.first_response_at is None:
        c.first_response_at = datetime.now(tz=UTC)
        await session.flush()

    msg = Mensagem(
        conversa_id=c.id,
        external_id=None,
        role=MensagemRole.ATENDENTE,
        content_encrypted=encrypt_pii(text),
    )
    session.add(msg)
    await session.flush()
    # Prefixa a mensagem enviada com '*<Nome do atendente>:*\n\n<texto>' pra o
    # cliente saber que eh humano (e nao mais o bot) e QUEM esta atendendo.
    # 2 quebras de linha separam o cabecalho do conteudo no WhatsApp.
    # No dashboard exibe sem o prefixo — eh adicionado so no envio outbound.
    atendente = await session.get(User, atendente_id)
    assinatura = _assinatura(atendente.name if atendente else None)
    # Idempotente: se o atendente ja digitou um cabecalho, nao duplica.
    limpo = text.lstrip()
    if limpo.lower().startswith("*suporte:*") or limpo.startswith(f"*{assinatura}:*"):
        text_outbound = text
    else:
        text_outbound = f"*{assinatura}:*\n\n{text}"
    # persist=False: a mensagem ja foi gravada acima como ATENDENTE. Sem isso o
    # worker gravava de novo como BOT ("*SUPORTE:* ...") e o chat mostrava 2x.
    enqueuer.enqueue_send_outbound(c.whatsapp, text_outbound, c.id, persist=False)

    if redis is not None:
        try:
            await publish_event(
                redis,
                c.id,
                {
                    "type": "msg",
                    "id": str(msg.id),
                    "role": "atendente",
                    "text": text,
                    "ts": msg.created_at.isoformat() if msg.created_at else None,
                },
            )
        except Exception:
            pass

    return msg
