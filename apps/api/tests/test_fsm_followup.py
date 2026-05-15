"""FSM: AGUARDA_FOLLOWUP_OS transitions."""
from __future__ import annotations

import pytest
from ondeline_api.db.models.business import ConversaEstado, ConversaStatus
from ondeline_api.domain.fsm import ActionKind, Event, EventKind, Fsm

pytestmark = pytest.mark.asyncio


def _event(text: str) -> Event:
    return Event(kind=EventKind.MSG_CLIENTE_TEXT, text=text)


def test_sim_retorna_confirmar() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
        status=ConversaStatus.BOT,
        event=_event("sim"),
    )
    assert d.new_estado is ConversaEstado.ENCERRADA
    assert any(a.kind is ActionKind.FOLLOWUP_OS_CONFIRMAR for a in d.actions)


def test_ok_retorna_confirmar() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
        status=ConversaStatus.BOT,
        event=_event("ok, obrigado!"),
    )
    assert d.new_estado is ConversaEstado.ENCERRADA
    assert any(a.kind is ActionKind.FOLLOWUP_OS_CONFIRMAR for a in d.actions)


def test_nao_retorna_escalar() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
        status=ConversaStatus.BOT,
        event=_event("não, continua sem internet"),
    )
    assert d.new_estado is ConversaEstado.AGUARDA_ATENDENTE
    assert any(a.kind is ActionKind.FOLLOWUP_OS_ESCALAR for a in d.actions)


def test_ambiguo_chama_llm() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
        status=ConversaStatus.BOT,
        event=_event("e as duas horas quanto vai demorar"),
    )
    assert d.new_estado is ConversaEstado.AGUARDA_FOLLOWUP_OS
    assert any(a.kind is ActionKind.LLM_TURN for a in d.actions)
