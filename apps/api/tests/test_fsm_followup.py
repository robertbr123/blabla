"""FSM: AGUARDA_FOLLOWUP_OS + AGUARDA_CSAT transitions."""
from __future__ import annotations

import pytest
from ondeline_api.db.models.business import ConversaEstado, ConversaStatus
from ondeline_api.domain.fsm import ActionKind, Event, EventKind, Fsm

pytestmark = pytest.mark.asyncio


def _event(text: str) -> Event:
    return Event(kind=EventKind.MSG_CLIENTE_TEXT, text=text)


def test_sim_sem_nota_vai_para_csat() -> None:
    # "Sim" sem nota: confirma que resolveu, mas NAO encerra — fica aguardando
    # a nota numa proxima mensagem (era aqui que o "5" se perdia).
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
        status=ConversaStatus.BOT,
        event=_event("sim"),
    )
    assert d.new_estado is ConversaEstado.AGUARDA_CSAT
    assert any(a.kind is ActionKind.FOLLOWUP_OS_CONFIRMAR for a in d.actions)


def test_ok_sem_nota_vai_para_csat() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
        status=ConversaStatus.BOT,
        event=_event("ok, obrigado!"),
    )
    assert d.new_estado is ConversaEstado.AGUARDA_CSAT
    assert any(a.kind is ActionKind.FOLLOWUP_OS_CONFIRMAR for a in d.actions)


def test_nota_alta_direto_encerra() -> None:
    # Nota presente ja na primeira resposta ("5" ou "sim, 5"): confirma + CSAT
    # capturado -> encerra direto.
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
        status=ConversaStatus.BOT,
        event=_event("5"),
    )
    assert d.new_estado is ConversaEstado.ENCERRADA
    assert any(a.kind is ActionKind.FOLLOWUP_OS_CONFIRMAR for a in d.actions)


def test_sim_com_nota_encerra() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
        status=ConversaStatus.BOT,
        event=_event("sim, nota 5"),
    )
    assert d.new_estado is ConversaEstado.ENCERRADA
    assert any(a.kind is ActionKind.FOLLOWUP_OS_CONFIRMAR for a in d.actions)


def test_nota_baixa_escala() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
        status=ConversaStatus.BOT,
        event=_event("2"),
    )
    assert d.new_estado is ConversaEstado.AGUARDA_ATENDENTE
    assert any(a.kind is ActionKind.FOLLOWUP_OS_ESCALAR for a in d.actions)


def test_nao_retorna_escalar() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
        status=ConversaStatus.BOT,
        event=_event("não, continua sem internet"),
    )
    assert d.new_estado is ConversaEstado.AGUARDA_ATENDENTE
    assert any(a.kind is ActionKind.FOLLOWUP_OS_ESCALAR for a in d.actions)


def test_ambiguo_nao_repergunta_followup() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
        status=ConversaStatus.BOT,
        event=_event("e as duas horas quanto vai demorar"),
    )
    assert d.new_estado is ConversaEstado.AGUARDA_FOLLOWUP_OS
    assert d.actions == []


def test_csat_recebe_nota_encerra() -> None:
    # Estado AGUARDA_CSAT (depois do "Sim"): o "5" solto agora e capturado.
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_CSAT,
        status=ConversaStatus.BOT,
        event=_event("5"),
    )
    assert d.new_estado is ConversaEstado.ENCERRADA
    assert any(a.kind is ActionKind.FOLLOWUP_OS_CONFIRMAR for a in d.actions)


def test_csat_nota_baixa_tambem_encerra() -> None:
    # Em AGUARDA_CSAT qualquer nota 1-5 registra CSAT e encerra (ja confirmou ok).
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_CSAT,
        status=ConversaStatus.BOT,
        event=_event("nota 1"),
    )
    assert d.new_estado is ConversaEstado.ENCERRADA
    assert any(a.kind is ActionKind.FOLLOWUP_OS_CONFIRMAR for a in d.actions)


def test_csat_sem_nota_vai_para_llm() -> None:
    # Cliente muda de assunto em vez de dar nota: encerra o follow-up e deixa o
    # LLM responder (nunca deixa o cliente no vacuo).
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_CSAT,
        status=ConversaStatus.BOT,
        event=_event("quanto custa o plano de 500 mega"),
    )
    assert d.new_estado is ConversaEstado.AGUARDA_OPCAO
    assert any(a.kind is ActionKind.LLM_TURN for a in d.actions)
