"""Loop tool-calling — happy path, com tool, max_iter, escalate."""
from __future__ import annotations

from uuid import uuid4

import ondeline_api.tools.consultar_planos

# Importing tools registers them into the global registry
import ondeline_api.tools.transferir_para_humano  # noqa: F401
import pytest
import respx
from fakeredis.aioredis import FakeRedis
from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.adapters.llm.base import (
    ChatRequest,
    ChatResponse,
    ToolCall,
)
from ondeline_api.adapters.llm.fakes import FakeLLMProvider
from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
)
from ondeline_api.repositories.mensagem import MensagemRepo
from ondeline_api.services.llm_loop import run_turn
from ondeline_api.services.tokens_budget import TokensBudget
from ondeline_api.tools.context import ToolContext
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

BASE = "http://evo.test"
INST = "hermes-wa"


def _build_ctx(db_session: AsyncSession, conv: Conversa, evolution: EvolutionAdapter) -> ToolContext:
    return ToolContext(
        session=db_session,
        conversa=conv,
        cliente=None,
        evolution=evolution,
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=None,  # type: ignore[arg-type]
    )


async def _seed_first_user_msg(db_session: AsyncSession, conv: Conversa) -> None:
    await MensagemRepo(db_session).insert_inbound_or_skip(
        conversa_id=conv.id,
        external_id=f"WAEVT_USER_{uuid4().hex[:8]}",
        text="Oi, quais sao os planos?",
        media_type=None,
        media_url=None,
    )
    await db_session.flush()


async def test_resposta_direta_sem_tool(db_session: AsyncSession) -> None:
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.AGUARDA_OPCAO,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await _seed_first_user_msg(db_session, conv)

    fake = FakeLLMProvider(
        responses=[
            ChatResponse(
                content="Ola! Posso ajudar?", tool_calls=[], tokens_used=20, finish_reason="stop"
            )
        ]
    )
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "OUT_1"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        out = await run_turn(
            ctx=_build_ctx(db_session, conv, adapter),
            provider=fake, model="Hermes-3", history_turns=12, max_iter=5, budget=None,
        )
        await adapter.aclose()
    assert out.final_text == "Ola! Posso ajudar?"
    assert out.escalated is False
    assert out.iterations == 1


async def test_chamada_tool_consultar_planos_e_resposta(db_session: AsyncSession) -> None:
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.AGUARDA_OPCAO,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await _seed_first_user_msg(db_session, conv)

    fake = FakeLLMProvider(
        responses=[
            ChatResponse(
                content=None,
                tool_calls=[ToolCall(id="c1", name="consultar_planos", arguments={})],
                tokens_used=15,
                finish_reason="tool_calls",
            ),
            ChatResponse(
                content="Temos Essencial, Plus e Premium! 🚀",
                tool_calls=[],
                tokens_used=25,
                finish_reason="stop",
            ),
        ]
    )
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "OUT_2"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        out = await run_turn(
            ctx=_build_ctx(db_session, conv, adapter),
            provider=fake, model="Hermes-3", history_turns=12, max_iter=5, budget=None,
        )
        await adapter.aclose()
    assert out.escalated is False
    assert out.tool_calls_made == ["consultar_planos"]
    assert "Essencial" in (out.final_text or "")


async def test_transferir_para_humano_escala_imediatamente(db_session: AsyncSession) -> None:
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.CLIENTE,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await _seed_first_user_msg(db_session, conv)

    fake = FakeLLMProvider(
        responses=[
            ChatResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c1",
                        name="transferir_para_humano",
                        arguments={"motivo": "cliente pediu"},
                    )
                ],
                tokens_used=10,
                finish_reason="tool_calls",
            )
        ]
    )
    adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
    out = await run_turn(
        ctx=_build_ctx(db_session, conv, adapter),
        provider=fake, model="Hermes-3", history_turns=12, max_iter=5, budget=None,
    )
    await adapter.aclose()
    assert out.escalated is True
    assert conv.estado is ConversaEstado.AGUARDA_ATENDENTE


async def test_provider_excecao_escala_com_mensagem_educada(db_session: AsyncSession) -> None:
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.AGUARDA_OPCAO,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await _seed_first_user_msg(db_session, conv)

    class BoomProvider(FakeLLMProvider):
        async def chat(self, req: ChatRequest) -> ChatResponse:
            raise RuntimeError("hermes off")

    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "OUT_3"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        out = await run_turn(
            ctx=_build_ctx(db_session, conv, adapter),
            provider=BoomProvider(responses=[]), model="Hermes-3",
            history_turns=12, max_iter=5, budget=None,
        )
        await adapter.aclose()
    assert out.escalated is True
    assert conv.status is ConversaStatus.AGUARDANDO


async def test_budget_excedido_escala_sem_chamar_provider(db_session: AsyncSession) -> None:
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.AGUARDA_OPCAO,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await _seed_first_user_msg(db_session, conv)

    redis = FakeRedis(decode_responses=False)
    budget = TokensBudget(redis, daily_limit=10)
    await budget.add(str(conv.id), 100)  # ja excedeu

    fake = FakeLLMProvider(responses=[])  # se chamar, exhausta
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "OUT_4"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        out = await run_turn(
            ctx=_build_ctx(db_session, conv, adapter),
            provider=fake, model="Hermes-3", history_turns=12, max_iter=5, budget=budget,
        )
        await adapter.aclose()
    assert out.escalated is True
