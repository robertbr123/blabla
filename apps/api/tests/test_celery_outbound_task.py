"""Task Celery send_outbound_task — escreve em Mensagem(role=BOT) + chama Evolution.

Em modo eager dentro de pytest-asyncio, `asyncio.run()` falha porque ja existe
um event loop ativo. Testamos diretamente a corotina `_run()`.

Nota sobre sessoes: `db_session` usa uma transacao pendente que nao e visivel
a outras conexoes. Para que a conversa seja visivel ao task_session() do worker,
criamos a conversa via `task_session()` (que commita imediatamente), nao via
`db_session`. A assertiva de persistencia usa tambem uma sessao fresca.

Cada teste usa um JID unico para evitar colisao com dados de execucoes anteriores.
"""
from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
import respx
from ondeline_api.config import get_settings
from ondeline_api.db.engine import get_sessionmaker, reset_engine_cache
from ondeline_api.repositories.conversa import ConversaRepo
from ondeline_api.workers.outbound import _run as outbound_run
from ondeline_api.workers.runtime import get_redis, reset_redis_cache, task_session

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset_engine() -> Generator[None, None, None]:
    """Limpa o cache do engine e do redis a cada teste (um event loop por teste)."""
    reset_redis_cache()
    yield
    reset_engine_cache()
    reset_redis_cache()


async def test_send_outbound_persists_and_calls_evolution() -> None:
    settings = get_settings()
    jid = f"outb_{uuid.uuid4().hex[:8]}@s.whatsapp.net"

    # Cria a conversa via task_session() para que fique commitada e visivel
    # a outras conexoes (db_session usa transacao pendente nao commitada).
    async with task_session() as session:
        conv = await ConversaRepo(session).get_or_create_by_whatsapp(jid)
    conversa_id = conv.id

    base = settings.evolution_url.rstrip("/")
    inst = settings.evolution_instance
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{base}/message/sendText/{inst}").respond(
            200, json={"key": {"id": "WAEVT_OUT_X"}}
        )
        out = await outbound_run(jid, "Recebi!", conversa_id)

    assert out["status"] == "ok"

    # Assertiva: mensagem do bot persistida. Usa sessao fresca apos o commit do task.
    from ondeline_api.db.models.business import Mensagem, MensagemRole
    from sqlalchemy import select

    sm = get_sessionmaker()
    async with sm() as fresh_session:
        msgs = (
            await fresh_session.execute(
                select(Mensagem).where(
                    Mensagem.conversa_id == conversa_id,
                    Mensagem.role == MensagemRole.BOT,
                )
            )
        ).scalars().all()
    assert len(msgs) == 1


async def test_send_outbound_idempotente_nao_reenvia() -> None:
    """Com a chave de idempotência já marcada (simula retry após envio), o worker
    NÃO chama o Evolution de novo, mas ainda persiste o bot_reply."""
    jid = f"outb_{uuid.uuid4().hex[:8]}@s.whatsapp.net"
    async with task_session() as session:
        conv = await ConversaRepo(session).get_or_create_by_whatsapp(jid)
    conversa_id = conv.id

    key = f"idem_{uuid.uuid4().hex[:8]}"
    redis = await get_redis()
    await redis.set(f"outbound:sent:{key}", "1", ex=60)

    # respx sem nenhuma rota: se o worker tentar enviar, levanta. Esperamos 0 calls.
    with respx.mock() as router:
        out = await outbound_run(jid, "Recebi!", conversa_id, key)
    assert out["status"] == "ok"
    assert router.calls.call_count == 0  # nao reenviou

    from ondeline_api.db.models.business import Mensagem, MensagemRole
    from sqlalchemy import select

    sm = get_sessionmaker()
    async with sm() as fresh_session:
        msgs = (
            await fresh_session.execute(
                select(Mensagem).where(
                    Mensagem.conversa_id == conversa_id,
                    Mensagem.role == MensagemRole.BOT,
                )
            )
        ).scalars().all()
    assert len(msgs) == 1  # bot_reply persistido mesmo sem reenviar


async def test_send_outbound_persist_false_so_envia() -> None:
    """Resposta do atendente: ja gravada como ATENDENTE pelo responder — o worker
    envia mas NAO grava de novo como BOT (o chat mostrava a mensagem 2x)."""
    settings = get_settings()
    jid = f"outb_{uuid.uuid4().hex[:8]}@s.whatsapp.net"
    async with task_session() as session:
        conv = await ConversaRepo(session).get_or_create_by_whatsapp(jid)
    conversa_id = conv.id

    base = settings.evolution_url.rstrip("/")
    inst = settings.evolution_instance
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{base}/message/sendText/{inst}").respond(
            200, json={"key": {"id": "WAEVT_OUT_Z"}}
        )
        out = await outbound_run(jid, "*SUPORTE:*\n\noi", conversa_id, persist=False)
    assert out["status"] == "ok"

    from ondeline_api.db.models.business import Mensagem
    from sqlalchemy import select

    sm = get_sessionmaker()
    async with sm() as fresh_session:
        msgs = (
            await fresh_session.execute(
                select(Mensagem).where(Mensagem.conversa_id == conversa_id)
            )
        ).scalars().all()
    assert msgs == []


async def test_send_outbound_publica_sse_com_id_da_mensagem() -> None:
    """O evento SSE leva o id do banco — e por ele que o dashboard deduplica."""
    import json

    from ondeline_api.db.models.business import Mensagem
    from ondeline_api.services.conversa_events import _channel
    from sqlalchemy import select

    settings = get_settings()
    jid = f"outb_{uuid.uuid4().hex[:8]}@s.whatsapp.net"
    async with task_session() as session:
        conv = await ConversaRepo(session).get_or_create_by_whatsapp(jid)
    conversa_id = conv.id

    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(_channel(conversa_id))
    try:
        base = settings.evolution_url.rstrip("/")
        inst = settings.evolution_instance
        with respx.mock(assert_all_called=True) as router:
            router.post(f"{base}/message/sendText/{inst}").respond(
                200, json={"key": {"id": "WAEVT_OUT_W"}}
            )
            await outbound_run(jid, "Oi!", conversa_id)

        event = None
        for _ in range(20):
            m = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
            if m is not None:
                event = json.loads(m["data"])
                break
    finally:
        await pubsub.unsubscribe()
        await pubsub.close()

    sm = get_sessionmaker()
    async with sm() as fresh_session:
        msg = (
            await fresh_session.execute(
                select(Mensagem).where(Mensagem.conversa_id == conversa_id)
            )
        ).scalar_one()
    assert event is not None
    assert event["id"] == str(msg.id)
