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
from ondeline_api.workers.runtime import task_session

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset_engine() -> Generator[None, None, None]:
    """Limpa o cache do engine apos cada teste."""
    yield
    reset_engine_cache()


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
