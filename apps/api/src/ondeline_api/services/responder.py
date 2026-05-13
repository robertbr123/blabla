"""Service: atendente responde mensagem na conversa.

Persiste Mensagem(role=ATENDENTE) e enfileira envio outbound via Celery.
Reusa BufferedOutboundEnqueuer para envio pos-commit.
"""
from __future__ import annotations

from typing import Protocol
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.crypto import encrypt_pii
from ondeline_api.db.models.business import Mensagem, MensagemRole
from ondeline_api.repositories.conversa import ConversaRepo
from ondeline_api.services.conversa_events import publish as publish_event


class _OutboundEnqueuer(Protocol):
    def enqueue_send_outbound(self, jid: str, text: str, conversa_id: UUID) -> None: ...


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

    msg = Mensagem(
        conversa_id=c.id,
        external_id=None,
        role=MensagemRole.ATENDENTE,
        content_encrypted=encrypt_pii(text),
    )
    session.add(msg)
    await session.flush()
    enqueuer.enqueue_send_outbound(c.whatsapp, text, c.id)

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
