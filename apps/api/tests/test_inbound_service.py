"""inbound.process_inbound_message — orquestracao testada com fakes.

Aqui isolamos a logica de "dado um InboundEvent + repositorios + adapter,
o que acontece?". Sem Celery, sem httpx real, sem Postgres real.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
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
    llm_turns: list[UUID] = field(default_factory=list)

    def enqueue_send_outbound(self, jid: str, text: str, conversa_id: UUID) -> None:
        self.sent.append((jid, text, conversa_id))

    def enqueue_llm_turn(self, conversa_id: UUID) -> None:
        self.llm_turns.append(conversa_id)


# ── FakeConfigSession ─────────────────────────────────────────


class _FakeScalar:
    def __init__(self, value: Any) -> None:
        self._v = value

    def scalar_one_or_none(self) -> Any:
        return self._v


class FakeConfigSession:
    """Fake AsyncSession suficiente para ConfigRepo.get('bot.ativo')."""

    def __init__(self, bot_ativo: Any = True) -> None:
        self._bot_ativo = bot_ativo

    async def execute(self, stmt: Any) -> _FakeScalar:  # noqa: ARG002
        return _FakeScalar(self._bot_ativo)


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


async def test_text_msg_inicio_enfileira_llm_turn() -> None:
    fake_msgs = FakeMensagemRepo()
    fake_out = FakeOutboundQueue()
    repos = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=fake_msgs,
        outbound=fake_out,
        ack_text="ACK!",
    )
    out = await process_inbound_message(_evt(), repos)
    assert out.persisted is True
    assert out.duplicate is False
    assert out.escalated is True
    assert len(fake_msgs.inserted) == 1
    assert fake_out.sent == []  # sem ack direto em M4
    assert len(fake_out.llm_turns) == 1
    assert fake_out.llm_turns[0] == out.conversa_id


async def test_duplicate_short_circuits_no_ack() -> None:
    fake_out = FakeOutboundQueue()
    repos = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=FakeMensagemRepo(dedup_ids={"E1"}),
        outbound=fake_out,
        ack_text="ACK!",
    )
    out = await process_inbound_message(_evt(eid="E1"), repos)
    assert out.duplicate is True
    assert out.persisted is False
    assert fake_out.sent == []


async def test_from_me_skipped() -> None:
    fake_msgs = FakeMensagemRepo()
    repos = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=fake_msgs,
        outbound=FakeOutboundQueue(),
        ack_text="ACK!",
    )
    out = await process_inbound_message(_evt(from_me=True), repos)
    assert out.skipped_reason == "from_me"
    assert fake_msgs.inserted == []


async def test_sticker_skipped_silently() -> None:
    fake_out = FakeOutboundQueue()
    repos = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=FakeMensagemRepo(),
        outbound=fake_out,
        ack_text="ACK!",
    )
    out = await process_inbound_message(
        _evt(kind=InboundKind.STICKER, text=None), repos
    )
    assert out.skipped_reason == "sticker"
    assert fake_out.sent == []


async def test_image_event_persists_e_enfileira_llm_turn() -> None:
    fake_msgs = FakeMensagemRepo()
    fake_out = FakeOutboundQueue()
    repos = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=fake_msgs,
        outbound=fake_out,
        ack_text="ACK!",
    )
    out = await process_inbound_message(
        _evt(kind=InboundKind.IMAGE, text=None), repos
    )
    assert out.persisted is True
    assert len(fake_msgs.inserted) == 1
    assert fake_msgs.inserted[0].media_type == "image"
    assert fake_out.sent == []  # sem ack direto em M4
    assert len(fake_out.llm_turns) == 1
    assert fake_out.llm_turns[0] == out.conversa_id


async def test_humano_nao_dispara_llm() -> None:
    """Em estado HUMANO, FSM nao emite LLM_TURN — mensagem e registrada, sem acao do bot."""
    fake_conv_repo = FakeConversaRepo()
    fake_out = FakeOutboundQueue()
    repos = InboundDeps(
        conversas=fake_conv_repo,
        mensagens=FakeMensagemRepo(),
        outbound=fake_out,
        ack_text="ACK!",
    )
    # 1a msg a partir de INICIO -> LLM_TURN enfileirado
    out1 = await process_inbound_message(_evt(eid="A"), repos)
    assert out1.escalated is True
    assert len(fake_out.llm_turns) == 1
    # Simula LLM tendo transferido para humano (tool transferir_para_humano)
    conversa = fake_conv_repo.by_jid["5511999@s"]
    conversa.estado = ConversaEstado.HUMANO
    conversa.status = ConversaStatus.AGUARDANDO
    # 2a msg do mesmo JID -> conversa em HUMANO, sem LLM_TURN, sem ack
    out2 = await process_inbound_message(_evt(eid="B"), repos)
    assert out2.escalated is False
    assert len(fake_out.llm_turns) == 1  # nenhum adicional
    assert fake_out.sent == []


async def test_bot_desativado_persiste_e_retorna_skipped() -> None:
    """Bot desativado: mensagem é salva mas retorna skipped_reason=bot_desativado."""
    fake_msgs = FakeMensagemRepo()
    fake_out = FakeOutboundQueue()
    deps = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=fake_msgs,
        outbound=fake_out,
        ack_text="ACK!",
        session=FakeConfigSession(bot_ativo=False),
    )
    out = await process_inbound_message(_evt(), deps)
    assert out.skipped_reason == "bot_desativado"
    assert out.persisted is True
    assert out.duplicate is False
    assert out.escalated is False
    assert len(fake_msgs.inserted) == 1
    assert fake_out.sent == []
    assert fake_out.llm_turns == []


async def test_bot_ativo_true_processa_normalmente() -> None:
    """Bot ativo (value=True): fluxo normal passa pela FSM."""
    fake_msgs = FakeMensagemRepo()
    fake_out = FakeOutboundQueue()
    deps = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=fake_msgs,
        outbound=fake_out,
        ack_text="ACK!",
        session=FakeConfigSession(bot_ativo=True),
    )
    out = await process_inbound_message(_evt(), deps)
    assert out.skipped_reason is None
    assert out.persisted is True
    assert len(fake_out.llm_turns) == 1


async def test_bot_ativo_none_processa_normalmente() -> None:
    """Bot ativo implícito (chave ausente, value=None): default é ativo."""
    fake_msgs = FakeMensagemRepo()
    fake_out = FakeOutboundQueue()
    deps = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=fake_msgs,
        outbound=fake_out,
        ack_text="ACK!",
        session=FakeConfigSession(bot_ativo=None),
    )
    out = await process_inbound_message(_evt(), deps)
    assert out.skipped_reason is None
    assert out.persisted is True
    assert len(fake_out.llm_turns) == 1
