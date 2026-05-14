"""Servico de processamento de mensagem entrante.

Orquestra: parser -> dedup -> get-or-create conversa -> FSM -> persiste
estado -> enfileira ack outbound. Pura logica; nao toca FastAPI nem Celery
diretamente. Recebe deps via `InboundDeps`. Os Fakes nos testes implementam
a mesma interface estrutural.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID

from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
    Mensagem,
)
from ondeline_api.domain.fsm import (
    ActionKind,
    Event,
    EventKind,
    Fsm,
    FsmDecision,
)
from ondeline_api.services.media_classifier import (
    CATEGORIES_ESCALATE,
    CATEGORY_ACK,
    CATEGORY_TAG,
    MediaCategory,
    classify_media,
)
from ondeline_api.webhook.parser import InboundEvent, InboundKind


class _ConversaRepoProto(Protocol):
    async def get_or_create_by_whatsapp(self, whatsapp: str) -> Conversa: ...
    async def update_estado_status(
        self, conversa: Conversa, *, estado: ConversaEstado, status: ConversaStatus
    ) -> None: ...
    async def set_cliente(self, conversa: Conversa, cliente_id: UUID) -> None: ...
    async def add_tag(self, conversa: Conversa, tag: str) -> None: ...


class _MensagemRepoProto(Protocol):
    async def insert_inbound_or_skip(
        self,
        *,
        conversa_id: UUID,
        external_id: str,
        text: str | None,
        media_type: str | None,
        media_url: str | None,
    ) -> Mensagem | None: ...
    async def insert_bot_reply(
        self, *, conversa_id: UUID, text: str
    ) -> Mensagem: ...


class _OutboundQueueProto(Protocol):
    def enqueue_send_outbound(self, jid: str, text: str, conversa_id: UUID) -> None: ...
    def enqueue_llm_turn(self, conversa_id: UUID) -> None: ...
    def enqueue_followup_os(self, conversa_id: UUID, resultado: str, resposta: str) -> None: ...


@dataclass
class InboundDeps:
    conversas: _ConversaRepoProto
    mensagens: _MensagemRepoProto
    outbound: _OutboundQueueProto
    ack_text: str
    redis: Any = field(default=None)  # aioredis.Redis | None — typed Any to keep deps loose


@dataclass
class InboundResult:
    conversa_id: UUID | None
    persisted: bool
    duplicate: bool
    escalated: bool
    skipped_reason: str | None = None


_MEDIA_KINDS = {
    InboundKind.IMAGE,
    InboundKind.AUDIO,
    InboundKind.VIDEO,
    InboundKind.DOCUMENT,
}


def _to_fsm_event(kind: InboundKind, text: str | None) -> Event:
    if kind is InboundKind.TEXT:
        return Event(kind=EventKind.MSG_CLIENTE_TEXT, text=text)
    return Event(kind=EventKind.MSG_CLIENTE_MEDIA, text=text)


async def process_inbound_message(
    evt: InboundEvent, deps: InboundDeps
) -> InboundResult:
    if evt.from_me:
        return InboundResult(
            conversa_id=None, persisted=False, duplicate=False, escalated=False, skipped_reason="from_me"
        )
    if evt.kind is InboundKind.STICKER:
        return InboundResult(
            conversa_id=None, persisted=False, duplicate=False, escalated=False, skipped_reason="sticker"
        )
    if evt.kind is InboundKind.TEXT and not evt.text:
        return InboundResult(
            conversa_id=None, persisted=False, duplicate=False, escalated=False, skipped_reason="empty_text"
        )

    conversa = await deps.conversas.get_or_create_by_whatsapp(evt.jid)

    media_type = evt.kind.value if evt.kind in _MEDIA_KINDS else None
    msg = await deps.mensagens.insert_inbound_or_skip(
        conversa_id=conversa.id,
        external_id=evt.external_id,
        text=evt.text,
        media_type=media_type,
        media_url=None,  # Evolution payload ja entrega midia hospedada; M3 nao baixa
    )
    if msg is None:
        return InboundResult(
            conversa_id=conversa.id, persisted=False, duplicate=True, escalated=False
        )

    # Intercepta midia para classificacao antes do FSM
    if evt.kind in _MEDIA_KINDS:
        category = classify_media(evt.kind, evt.text)
        ack = CATEGORY_ACK[category]
        tag = CATEGORY_TAG.get(category)

        if tag:
            await deps.conversas.add_tag(conversa, tag)

        if category is MediaCategory.AUDIO:
            # Nao escala — apenas avisa cliente e continua no estado atual
            deps.outbound.enqueue_send_outbound(evt.jid, ack, conversa.id)
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
            )

        if category in CATEGORIES_ESCALATE:
            # Avisa cliente e escala para humano
            deps.outbound.enqueue_send_outbound(evt.jid, ack, conversa.id)
            await deps.conversas.update_estado_status(
                conversa,
                estado=ConversaEstado.AGUARDA_ATENDENTE,
                status=ConversaStatus.AGUARDANDO,
            )
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=True
            )

    if deps.redis is not None:
        try:
            from ondeline_api.services.conversa_events import publish as _pub
            await _pub(
                deps.redis,
                conversa.id,
                {
                    "type": "msg",
                    "id": str(msg.id),
                    "role": "cliente",
                    "text": evt.text,
                    "ts": msg.created_at.isoformat() if msg.created_at else None,
                },
            )
        except Exception:
            pass

    decision: FsmDecision = Fsm.transition(
        estado=conversa.estado,
        status=conversa.status,
        event=_to_fsm_event(evt.kind, evt.text),
    )
    await deps.conversas.update_estado_status(
        conversa, estado=decision.new_estado, status=decision.new_status
    )

    escalated = False
    llm_turn_requested = False
    for action in decision.actions:
        if action.kind is ActionKind.LLM_TURN:
            llm_turn_requested = True
        elif action.kind is ActionKind.SEND_ACK:
            # Backward compat M3 — nao usado em M4 (FSM nao emite mais SEND_ACK)
            deps.outbound.enqueue_send_outbound(evt.jid, deps.ack_text, conversa.id)
            escalated = True
        elif action.kind is ActionKind.FOLLOWUP_OS_CONFIRMAR:
            deps.outbound.enqueue_followup_os(
                conversa.id, resultado="ok", resposta=evt.text or ""
            )
        elif action.kind is ActionKind.FOLLOWUP_OS_ESCALAR:
            deps.outbound.enqueue_followup_os(
                conversa.id, resultado="nao_ok", resposta=evt.text or ""
            )

    if llm_turn_requested:
        deps.outbound.enqueue_llm_turn(conversa.id)
        escalated = True

    return InboundResult(
        conversa_id=conversa.id,
        persisted=True,
        duplicate=False,
        escalated=escalated,
    )
