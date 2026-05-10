"""Maquina de estados da Conversa.

M3 entrega apenas a transicao minima de infra:
  INICIO | ENCERRADA -> HUMANO + ack
  HUMANO -> HUMANO (sem nova resposta)

M4 amplia para INICIO -> AGUARDA_OPCAO -> CLIENTE_CPF -> CLIENTE -> ...
controlado por tools do LLM.

Funcao pura: nao toca DB, Redis, httpx ou logger. Recebe (estado, status, event)
e devolve `FsmDecision(new_estado, new_status, actions)`. As actions sao
intents ('SEND_ACK') que o service traduz em chamadas concretas (Evolution + DB).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ondeline_api.db.models.business import ConversaEstado, ConversaStatus


class EventKind(StrEnum):
    MSG_CLIENTE_TEXT = "msg_cliente_text"
    MSG_CLIENTE_MEDIA = "msg_cliente_media"
    MSG_FROM_ME = "msg_from_me"  # bot/atendente — FSM nao deve ver isso (filter antes)


class ActionKind(StrEnum):
    SEND_ACK = "send_ack"


@dataclass(frozen=True, slots=True)
class Event:
    kind: EventKind
    text: str | None


@dataclass(frozen=True, slots=True)
class Action:
    kind: ActionKind
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FsmDecision:
    new_estado: ConversaEstado
    new_status: ConversaStatus
    actions: list[Action]


class InvalidTransition(Exception):
    pass


class Fsm:
    """Stateless FSM — nao tem `self`. Composto de regras puras."""

    @staticmethod
    def transition(
        estado: ConversaEstado,
        status: ConversaStatus,
        event: Event,
    ) -> FsmDecision:
        if event.kind is EventKind.MSG_FROM_ME:
            raise InvalidTransition(
                "FSM should never receive MSG_FROM_ME — filter before invoking."
            )

        # M3: qualquer mensagem do cliente em INICIO ou ENCERRADA reabre/inicia
        # e escala para humano com ack. Em HUMANO/AGUARDANDO, apenas registra.
        if estado in (ConversaEstado.INICIO, ConversaEstado.ENCERRADA):
            return FsmDecision(
                new_estado=ConversaEstado.HUMANO,
                new_status=ConversaStatus.AGUARDANDO,
                actions=[Action(kind=ActionKind.SEND_ACK)],
            )

        # ja em humano — nao reenvia ack
        return FsmDecision(
            new_estado=ConversaEstado.HUMANO,
            new_status=ConversaStatus.AGUARDANDO,
            actions=[],
        )
