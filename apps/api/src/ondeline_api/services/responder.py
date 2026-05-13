"""Service: atendente responde mensagem na conversa.

Persiste Mensagem(role=ATENDENTE) e enfileira envio outbound via Celery.
Reusa BufferedOutboundEnqueuer para envio pos-commit.
"""
from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.crypto import encrypt_pii
from ondeline_api.db.models.business import Mensagem, MensagemRole
from ondeline_api.repositories.conversa import ConversaRepo


class _OutboundEnqueuer(Protocol):
    def enqueue_send_outbound(self, jid: str, text: str, conversa_id: UUID) -> None: ...


async def responder(
    session: AsyncSession,
    conversa_id: UUID,
    atendente_id: UUID,
    text: str,
    enqueuer: _OutboundEnqueuer,
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
    return msg
