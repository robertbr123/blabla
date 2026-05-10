"""Helpers usados pelas tasks Celery.

Cada task abre seu proprio event loop com `asyncio.run()` e seu proprio
`AsyncSession`. Conexoes nao sao compartilhadas entre invocacoes — simples
e correto, custa um connect/close por task (~1ms para Postgres local).

`celery_outbound_enqueuer()` e o adapter que satisfaz `_OutboundQueueProto`
do service: chama `.delay()` na task de saida ao inves de virar lambda
in-process.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.engine import get_sessionmaker
from ondeline_api.services.inbound import _OutboundQueueProto


@asynccontextmanager
async def task_session() -> AsyncIterator[AsyncSession]:
    """Yields a fresh AsyncSession bound a uma transacao. Commit no exit limpo,
    rollback em excecao.
    """
    factory = get_sessionmaker()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


class CeleryOutboundEnqueuer(_OutboundQueueProto):
    """Adapter pro service: enfileira via task Celery em vez de lista in-mem."""

    def enqueue_send_outbound(self, jid: str, text: str, conversa_id: UUID) -> None:
        # Import local pra evitar ciclo (outbound.py importa runtime indiretamente).
        from ondeline_api.workers.outbound import send_outbound_task

        send_outbound_task.delay(jid=jid, text=text, conversa_id=str(conversa_id))
