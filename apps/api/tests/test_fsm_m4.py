"""FSM M4 — transicoes adicionais e LLM_TURN action."""
from __future__ import annotations

from ondeline_api.db.models.business import ConversaEstado, ConversaStatus
from ondeline_api.domain.fsm import (
    ActionKind,
    Event,
    EventKind,
    Fsm,
)


def test_aguarda_opcao_segunda_msg_continua_em_aguarda_opcao() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_OPCAO,
        status=ConversaStatus.BOT,
        event=Event(kind=EventKind.MSG_CLIENTE_TEXT, text="quero ser cliente"),
    )
    assert d.new_estado is ConversaEstado.AGUARDA_OPCAO
    assert any(a.kind is ActionKind.LLM_TURN for a in d.actions)


def test_cliente_estado_continua_chamando_llm() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.CLIENTE,
        status=ConversaStatus.BOT,
        event=Event(kind=EventKind.MSG_CLIENTE_TEXT, text="quero 2a via"),
    )
    assert d.new_estado is ConversaEstado.CLIENTE
    assert any(a.kind is ActionKind.LLM_TURN for a in d.actions)


def test_aguarda_atendente_nao_chama_llm() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_ATENDENTE,
        status=ConversaStatus.AGUARDANDO,
        event=Event(kind=EventKind.MSG_CLIENTE_TEXT, text="oi atendente"),
    )
    assert d.actions == []
