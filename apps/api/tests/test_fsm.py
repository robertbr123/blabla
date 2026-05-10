"""Maquina de estados de Conversa (M4 — comportamento atualizado)."""
from __future__ import annotations

import pytest
from ondeline_api.db.models.business import ConversaEstado, ConversaStatus
from ondeline_api.domain.fsm import (
    ActionKind,
    Event,
    EventKind,
    Fsm,
    InvalidTransition,
)


def test_inicio_recebe_msg_cliente_vai_para_aguarda_opcao_com_llm_turn() -> None:
    decision = Fsm.transition(
        estado=ConversaEstado.INICIO,
        status=ConversaStatus.BOT,
        event=Event(kind=EventKind.MSG_CLIENTE_TEXT, text="Oi"),
    )
    assert decision.new_estado is ConversaEstado.AGUARDA_OPCAO
    assert decision.new_status is ConversaStatus.BOT
    assert any(a.kind is ActionKind.LLM_TURN for a in decision.actions)


def test_humano_recebe_msg_cliente_apenas_persiste_sem_responder() -> None:
    decision = Fsm.transition(
        estado=ConversaEstado.HUMANO,
        status=ConversaStatus.AGUARDANDO,
        event=Event(kind=EventKind.MSG_CLIENTE_TEXT, text="Cade?"),
    )
    assert decision.new_estado is ConversaEstado.HUMANO
    assert decision.new_status is ConversaStatus.AGUARDANDO
    assert decision.actions == []


def test_inicio_recebe_imagem_dispara_llm_turn() -> None:
    decision = Fsm.transition(
        estado=ConversaEstado.INICIO,
        status=ConversaStatus.BOT,
        event=Event(kind=EventKind.MSG_CLIENTE_MEDIA, text=None),
    )
    assert decision.new_estado is ConversaEstado.AGUARDA_OPCAO
    assert any(a.kind is ActionKind.LLM_TURN for a in decision.actions)


def test_encerrada_recebe_msg_reabre_e_dispara_llm_turn() -> None:
    decision = Fsm.transition(
        estado=ConversaEstado.ENCERRADA,
        status=ConversaStatus.ENCERRADA,
        event=Event(kind=EventKind.MSG_CLIENTE_TEXT, text="oi de novo"),
    )
    assert decision.new_estado is ConversaEstado.AGUARDA_OPCAO
    assert decision.new_status is ConversaStatus.BOT
    assert any(a.kind is ActionKind.LLM_TURN for a in decision.actions)


def test_evento_invalido_levanta() -> None:
    with pytest.raises(InvalidTransition):
        Fsm.transition(
            estado=ConversaEstado.INICIO,
            status=ConversaStatus.BOT,
            event=Event(kind=EventKind.MSG_FROM_ME, text=None),
        )
