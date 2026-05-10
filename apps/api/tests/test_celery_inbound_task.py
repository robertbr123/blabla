"""Task Celery process_inbound_message_task — testa logica _run + Postgres real.

Em modo eager dentro de pytest-asyncio, `asyncio.run()` falha porque ja existe
um event loop ativo. Testamos diretamente a corotina `_run()`, que contem toda
a logica; o decorator @celery_app.task e apenas um wrapper de despacho.

Nota sobre sessoes: `_run()` usa `task_session()` que commita no DB real.
Por isso, cada teste usa um JID e external_id unicos para evitar colisoes
com dados de execucoes anteriores.

Nota sobre dedup: o mecanismo de dedup depende de UNIQUE(external_id, created_at)
numa tabela particionada por created_at. Como duas invocacoes de _run() distintas
sempre geram created_at diferentes, o dedup entre tasks separadas nao e garantido
pelo indice da tabela-pai — e responsabilidade da camada de mensageria (idempotency
key do broker). O dedup intra-transacao ja e coberto por test_repo_mensagem.py.
Aqui testamos: parse_error skip e task retorna estrutura correta.
"""
from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from ondeline_api.db.engine import reset_engine_cache
from ondeline_api.workers.inbound import _run

pytestmark = pytest.mark.asyncio


def _payload(jid: str, external_id: str, from_me: bool = False) -> dict[str, Any]:
    return {
        "event": "messages.upsert",
        "data": {
            "key": {"id": external_id, "remoteJid": jid, "fromMe": from_me},
            "pushName": "Maria",
            "message": {"conversation": "Oi"},
        },
    }


@pytest.fixture(autouse=True)
def _reset_engine() -> Generator[None, None, None]:
    """Limpa o cache do engine apos cada teste para que o proximo teste
    crie um pool fresco no novo event loop.
    """
    yield
    reset_engine_cache()


@pytest.fixture
def _outbound_no_op(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Substitui send_outbound_task.delay e llm_turn_task.delay por no-op para isolar o inbound."""
    captured: list[dict[str, Any]] = []

    def fake_delay(**kwargs: Any) -> None:
        captured.append(kwargs)

    monkeypatch.setattr(
        "ondeline_api.workers.outbound.send_outbound_task.delay", fake_delay
    )
    monkeypatch.setattr(
        "ondeline_api.workers.llm_turn.llm_turn_task.delay", fake_delay
    )
    return captured


async def test_task_processes_first_message(_outbound_no_op) -> None:
    import uuid
    jid = f"inb_new_{uuid.uuid4().hex[:8]}@s.whatsapp.net"
    result = await _run(_payload(jid, external_id=f"EVT_{uuid.uuid4().hex[:8]}"))
    assert result["persisted"] is True
    assert result["duplicate"] is False
    assert result["escalated"] is True
    # M4: llm_turn_task.delay e chamado (nao send_outbound_task.delay)
    assert len(_outbound_no_op) == 1
    assert "conversa_id" in _outbound_no_op[0]


async def test_task_returns_parse_error_on_bad_payload(_outbound_no_op) -> None:
    """Payload com event errado e silenciosamente descartado — sem DB, sem ack."""
    bad_payload = {"event": "messages.delete", "data": {}}
    result = await _run(bad_payload)
    assert result["skipped"] == "parse_error"
    assert "error" in result
    assert _outbound_no_op == []


async def test_task_skips_from_me(_outbound_no_op) -> None:
    import uuid
    jid = f"inb_fromme_{uuid.uuid4().hex[:8]}@s.whatsapp.net"
    out = await _run(_payload(jid, external_id=f"EVT_{uuid.uuid4().hex[:8]}", from_me=True))
    assert out["skipped_reason"] == "from_me"
    assert _outbound_no_op == []
