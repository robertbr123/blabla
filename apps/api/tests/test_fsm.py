"""Maquina de estados de Conversa (M3 — minima)."""
from __future__ import annotations

import pytest
from ondeline_api.db.models.business import ConversaEstado, ConversaStatus
from ondeline_api.domain.fsm import (
    ActionKind,
    Event,
    EventKind,
    Fsm,
    FsmDecision,
    InvalidTransition,
)


def test_inicio_recebe_msg_cliente_vai_para_humano_e_envia_ack() -> None:
    decision = Fsm.transition(
        estado=ConversaEstado.INICIO,
        status=ConversaStatus.BOT,
        event=Event(kind=EventKind.MSG_CLIENTE_TEXT, text="Oi"),
    )
    assert isinstance(decision, FsmDecision)
    assert decision.new_estado is ConversaEstado.HUMANO
    assert decision.new_status is ConversaStatus.AGUARDANDO
    assert any(a.kind is ActionKind.SEND_ACK for a in decision.actions)


def test_humano_recebe_msg_cliente_apenas_persiste_sem_responder() -> None:
    """Conversa ja aguardando atendente — nao reenvia ack a cada msg."""
    decision = Fsm.transition(
        estado=ConversaEstado.HUMANO,
        status=ConversaStatus.AGUARDANDO,
        event=Event(kind=EventKind.MSG_CLIENTE_TEXT, text="Cade?"),
    )
    assert decision.new_estado is ConversaEstado.HUMANO
    assert decision.new_status is ConversaStatus.AGUARDANDO
    assert decision.actions == []


def test_inicio_recebe_imagem_ack_e_humano() -> None:
    decision = Fsm.transition(
        estado=ConversaEstado.INICIO,
        status=ConversaStatus.BOT,
        event=Event(kind=EventKind.MSG_CLIENTE_MEDIA, text=None),
    )
    assert decision.new_estado is ConversaEstado.HUMANO
    assert any(a.kind is ActionKind.SEND_ACK for a in decision.actions)


def test_encerrada_recebe_msg_reabre_e_envia_ack() -> None:
    decision = Fsm.transition(
        estado=ConversaEstado.ENCERRADA,
        status=ConversaStatus.ENCERRADA,
        event=Event(kind=EventKind.MSG_CLIENTE_TEXT, text="oi de novo"),
    )
    assert decision.new_estado is ConversaEstado.HUMANO
    assert decision.new_status is ConversaStatus.AGUARDANDO
    assert any(a.kind is ActionKind.SEND_ACK for a in decision.actions)


def test_evento_invalido_levanta() -> None:
    with pytest.raises(InvalidTransition):
        Fsm.transition(
            estado=ConversaEstado.INICIO,
            status=ConversaStatus.BOT,
            event=Event(kind=EventKind.MSG_FROM_ME, text=None),
        )


def test_action_send_ack_carrega_texto_default() -> None:
    decision = Fsm.transition(
        estado=ConversaEstado.INICIO,
        status=ConversaStatus.BOT,
        event=Event(kind=EventKind.MSG_CLIENTE_TEXT, text="oi"),
    )
    ack = next(a for a in decision.actions if a.kind is ActionKind.SEND_ACK)
    # texto vazio -> service usa BOT_ACK_TEXT do settings; FSM apenas sinaliza intent
    assert ack.payload == {}
