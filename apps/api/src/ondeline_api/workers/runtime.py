"""Helpers usados pelas tasks Celery.

Cada task abre seu proprio event loop com `asyncio.run()` e seu proprio
`AsyncSession`. Conexoes nao sao compartilhadas entre invocacoes — simples
e correto, custa um connect/close por task (~1ms para Postgres local).

`CeleryOutboundEnqueuer` e o adapter que satisfaz `_OutboundQueueProto`
do service: chama `.delay()` na task de saida ao inves de virar lambda
in-process.

`BufferedOutboundEnqueuer` coleta as chamadas durante a sessao e dispara
APOS o commit. Isso e necessario em modo eager (task_always_eager=True)
pois o `.delay()` executaria a task outbound sincronamente ANTES do commit
da sessao inbound — causando FK violation ao tentar inserir mensagens com
uma conversa ainda nao commitada.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.engine import get_sessionmaker, reset_engine_cache
from ondeline_api.services.inbound import _OutboundQueueProto

_T = TypeVar("_T")

_redis_singleton: aioredis.Redis[bytes] | None = None


async def get_redis() -> aioredis.Redis[bytes]:
    global _redis_singleton
    if _redis_singleton is None:
        from ondeline_api.config import get_settings

        _redis_singleton = aioredis.from_url(get_settings().redis_url, decode_responses=False)
    return _redis_singleton


def reset_redis_cache() -> None:
    """Reset the Redis singleton. Call when entering a new event loop."""
    global _redis_singleton
    _redis_singleton = None


def run_task(coro_factory: Callable[[], Any]) -> Any:
    """Run an async coroutine factory in a fresh event loop.

    Always resets the SQLAlchemy engine cache and Redis singleton before
    calling asyncio.run() so that asyncpg pools are never reused across
    different event loops (which causes 'Future attached to a different loop').

    When called from inside a running loop (e.g. TestClient eager mode), spawns
    a thread with its own loop instead.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    reset_engine_cache()
    reset_redis_cache()

    if loop is not None and loop.is_running():
        def _thread() -> Any:
            reset_engine_cache()
            reset_redis_cache()
            return asyncio.run(coro_factory())

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(_thread).result()

    return asyncio.run(coro_factory())


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

    def enqueue_llm_turn(self, conversa_id: UUID) -> None:
        from ondeline_api.workers.llm_turn import llm_turn_task

        llm_turn_task.delay(conversa_id=str(conversa_id))

    def enqueue_followup_os(self, conversa_id: UUID, resultado: str, resposta: str) -> None:
        from ondeline_api.workers.followup import followup_os_task

        followup_os_task.delay(conversa_id=str(conversa_id), resultado=resultado, resposta=resposta)


@dataclass
class BufferedOutboundEnqueuer(_OutboundQueueProto):
    """Coleta chamadas enqueue_send_outbound e enqueue_llm_turn durante a sessao DB
    e armazena em buffer. Apos o commit da sessao, chame `.flush()` para disparar as
    tasks Celery. Isso garante que as tasks so rodam apos os dados inbound estarem
    commitados — critico em modo eager onde `.delay()` executa sincronamente.
    """

    _pending_outbound: list[dict[str, Any]] = field(default_factory=list)
    _pending_llm_turns: list[UUID] = field(default_factory=list)
    _pending_followup: list[dict[str, Any]] = field(default_factory=list)

    def enqueue_send_outbound(self, jid: str, text: str, conversa_id: UUID) -> None:
        self._pending_outbound.append({"jid": jid, "text": text, "conversa_id": str(conversa_id)})

    def enqueue_llm_turn(self, conversa_id: UUID) -> None:
        self._pending_llm_turns.append(conversa_id)

    def enqueue_followup_os(self, conversa_id: UUID, resultado: str, resposta: str) -> None:
        self._pending_followup.append({
            "conversa_id": str(conversa_id), "resultado": resultado, "resposta": resposta
        })

    def flush(self) -> None:
        """Dispara todas as tasks Celery pendentes. Chame APOS o commit da sessao."""
        from ondeline_api.workers.followup import followup_os_task
        from ondeline_api.workers.llm_turn import llm_turn_task
        from ondeline_api.workers.outbound import send_outbound_task

        for item in self._pending_outbound:
            send_outbound_task.delay(**item)
        for cid in self._pending_llm_turns:
            llm_turn_task.delay(conversa_id=str(cid))
        for item in self._pending_followup:
            followup_os_task.delay(**item)
        self._pending_outbound.clear()
        self._pending_llm_turns.clear()
        self._pending_followup.clear()
