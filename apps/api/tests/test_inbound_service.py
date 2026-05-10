"""inbound.process_inbound_message — orquestracao testada com fakes.

Aqui isolamos a logica de "dado um InboundEvent + repositorios + adapter,
o que acontece?". Sem Celery, sem httpx real, sem Postgres real.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest

from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
    Mensagem,
    MensagemRole,
)
from ondeline_api.services.inbound import InboundDeps, process_inbound_message
from ondeline_api.webhook.parser import InboundEvent, InboundKind


pytestmark = pytest.mark.asyncio


# ── Fakes ────────────────────────────────────────────────────


class FakeConversaRepo:
    def __init__(self) -> None:
        self.by_jid: dict[str, Conversa] = {}

    async def get_or_create_by_whatsapp(self, whatsapp: str) -> Conversa:
        if whatsapp in self.by_jid:
            return self.by_jid[whatsapp]
        c = Conversa(
            id=uuid4(),
            whatsapp=whatsapp,
            estado=ConversaEstado.INICIO,
            status=ConversaStatus.BOT,
        )
        self.by_jid[whatsapp] = c
        return c

    async def update_estado_status(
        self, conversa: Conversa, *, estado: ConversaEstado, status: ConversaStatus
    ) -> None:
        conversa.estado = estado
        conversa.status = status

    async def set_cliente(self, conversa: Conversa, cliente_id: UUID) -> None:
        conversa.cliente_id = cliente_id


class FakeMensagemRepo:
    def __init__(self, dedup_ids: set[str] | None = None) -> None:
        self.inserted: list[Mensagem] = []
        self.dedup_ids = dedup_ids or set()

    async def insert_inbound_or_skip(
        self, *, conversa_id, external_id, text, media_type, media_url
    ):
        if external_id in self.dedup_ids:
            return None
        m = Mensagem(
            id=uuid4(),
            conversa_id=conversa_id,
            external_id=external_id,
            role=MensagemRole.CLIENTE,
            content_encrypted=text,
            media_type=media_type,
            media_url=media_url,
        )
        self.inserted.append(m)
        return m

    async def insert_bot_reply(self, *, conversa_id, text):
        m = Mensagem(
            id=uuid4(),
            conversa_id=conversa_id,
            role=MensagemRole.BOT,
            content_encrypted=text,
        )
        self.inserted.append(m)
        return m


@dataclass
class FakeOutboundQueue:
    sent: list[tuple[str, str, UUID]] = field(default_factory=list)

    def enqueue_send_outbound(self, jid: str, text: str, conversa_id: UUID) -> None:
        self.sent.append((jid, text, conversa_id))


def _evt(kind=InboundKind.TEXT, text="Oi", from_me=False, eid="E1") -> InboundEvent:
    return InboundEvent(
        external_id=eid,
        jid="5511999@s",
        push_name="Maria",
        kind=kind,
        text=text,
        from_me=from_me,
    )


# ── Tests ────────────────────────────────────────────────────


async def test_text_msg_inicio_envia_ack_e_marca_humano() -> None:
    repos = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=FakeMensagemRepo(),
        outbound=FakeOutboundQueue(),
        ack_text="ACK!",
    )
    out = await process_inbound_message(_evt(), repos)
    assert out.persisted is True
    assert out.duplicate is False
    assert out.escalated is True
    assert len(repos.mensagens.inserted) == 1
    assert repos.outbound.sent == [("5511999@s", "ACK!", out.conversa_id)]


async def test_duplicate_short_circuits_no_ack() -> None:
    repos = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=FakeMensagemRepo(dedup_ids={"E1"}),
        outbound=FakeOutboundQueue(),
        ack_text="ACK!",
    )
    out = await process_inbound_message(_evt(eid="E1"), repos)
    assert out.duplicate is True
    assert out.persisted is False
    assert repos.outbound.sent == []


async def test_from_me_skipped() -> None:
    repos = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=FakeMensagemRepo(),
        outbound=FakeOutboundQueue(),
        ack_text="ACK!",
    )
    out = await process_inbound_message(_evt(from_me=True), repos)
    assert out.skipped_reason == "from_me"
    assert repos.mensagens.inserted == []


async def test_sticker_skipped_silently() -> None:
    repos = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=FakeMensagemRepo(),
        outbound=FakeOutboundQueue(),
        ack_text="ACK!",
    )
    out = await process_inbound_message(
        _evt(kind=InboundKind.STICKER, text=None), repos
    )
    assert out.skipped_reason == "sticker"
    assert repos.outbound.sent == []


async def test_image_event_persists_e_envia_ack() -> None:
    repos = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=FakeMensagemRepo(),
        outbound=FakeOutboundQueue(),
        ack_text="ACK!",
    )
    out = await process_inbound_message(
        _evt(kind=InboundKind.IMAGE, text=None), repos
    )
    assert out.persisted is True
    assert len(repos.mensagens.inserted) == 1
    assert repos.mensagens.inserted[0].media_type == "image"
    assert len(repos.outbound.sent) == 1


async def test_humano_nao_envia_ack_repetido() -> None:
    repos = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=FakeMensagemRepo(),
        outbound=FakeOutboundQueue(),
        ack_text="ACK!",
    )
    # 1a msg -> escala
    out1 = await process_inbound_message(_evt(eid="A"), repos)
    assert out1.escalated is True
    assert len(repos.outbound.sent) == 1
    # 2a msg do mesmo JID -> conversa ja em HUMANO, sem novo ack
    out2 = await process_inbound_message(_evt(eid="B"), repos)
    assert out2.escalated is False
    assert len(repos.outbound.sent) == 1
