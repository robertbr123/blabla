"""Maquina de estados da Conversa.

M3 entregou a transicao minima de infra.
M4 amplia para INICIO -> AGUARDA_OPCAO -> CLIENTE_CPF -> CLIENTE -> ...
controlado por tools do LLM.

Funcao pura: nao toca DB, Redis, httpx ou logger. Recebe (estado, status, event)
e devolve `FsmDecision(new_estado, new_status, actions)`. As actions sao
intents ('LLM_TURN', 'SEND_ACK') que o service traduz em chamadas concretas.
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
    LLM_TURN = "llm_turn"  # M4: pede ao service que rode 1 turno LLM
    FOLLOWUP_OS_CONFIRMAR = "followup_os_confirmar"  # cliente confirmou que OS resolveu
    FOLLOWUP_OS_ESCALAR = "followup_os_escalar"  # cliente disse que problema persiste


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


_PALAVRAS_OK = {
    "sim", "ok", "obrigado", "certo", "tudo bem", "já está", "resolveu",
    "funcionou", "ótimo", "otimo",
}
_PALAVRAS_NOK = {
    "não", "nao", "ainda não", "ainda nao", "continua", "sem sinal",
    "sem internet", "mesmo problema", "não resolveu", "nao resolveu",
}


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

        # ja em humano: registrar e aguardar atendente — NAO chama LLM, NAO envia ack
        if estado in (ConversaEstado.HUMANO, ConversaEstado.AGUARDA_ATENDENTE):
            return FsmDecision(
                new_estado=estado,
                new_status=status,
                actions=[],
            )

        # estados de coleta sequencial: inbound.py intercepta antes do LLM
        if estado in (ConversaEstado.MUDANCA_ENDERECO, ConversaEstado.CHECKLIST_OS):
            return FsmDecision(
                new_estado=estado,
                new_status=status,
                actions=[],
            )

        # aguarda confirmacao de follow-up: classifica deterministicamente antes de chamar LLM
        if estado is ConversaEstado.AGUARDA_FOLLOWUP_OS:
            text_norm = (event.text or "").lower().strip()
            if any(p in text_norm for p in _PALAVRAS_OK):
                return FsmDecision(
                    new_estado=ConversaEstado.ENCERRADA,
                    new_status=ConversaStatus.ENCERRADA,
                    actions=[Action(kind=ActionKind.FOLLOWUP_OS_CONFIRMAR)],
                )
            if any(p in text_norm for p in _PALAVRAS_NOK):
                return FsmDecision(
                    new_estado=ConversaEstado.AGUARDA_ATENDENTE,
                    new_status=ConversaStatus.AGUARDANDO,
                    actions=[Action(kind=ActionKind.FOLLOWUP_OS_ESCALAR)],
                )
            # ambiguo: LLM decide
            return FsmDecision(
                new_estado=ConversaEstado.AGUARDA_FOLLOWUP_OS,
                new_status=ConversaStatus.BOT,
                actions=[Action(kind=ActionKind.LLM_TURN)],
            )

        # encerrada: reabre + LLM cuida da nova interacao desde o inicio
        if estado is ConversaEstado.ENCERRADA:
            return FsmDecision(
                new_estado=ConversaEstado.AGUARDA_OPCAO,
                new_status=ConversaStatus.BOT,
                actions=[Action(kind=ActionKind.LLM_TURN)],
            )

        # demais (INICIO/AGUARDA_OPCAO/CLIENTE_CPF/CLIENTE/LEAD_*): LLM responde.
        # FSM nao decide o destino exato — o LLM, via tool transferir_para_humano,
        # eventualmente move para AGUARDA_ATENDENTE.
        if estado is ConversaEstado.INICIO:
            new_estado = ConversaEstado.AGUARDA_OPCAO
        else:
            new_estado = estado

        return FsmDecision(
            new_estado=new_estado,
            new_status=ConversaStatus.BOT,
            actions=[Action(kind=ActionKind.LLM_TURN)],
        )
