"""E2E sintetico do fluxo LLM:
  cliente: 'Oi'
  bot: 'Pode passar o CPF?'  (FakeLLM resp 1)
  cliente: '11122233344'
  bot: tool buscar_cliente_sgp -> tool resp ok -> bot 'Encontrei!'  (FakeLLM resp 2 + 3)
  cliente: 'manda boleto'
  bot: tool enviar_boleto -> bot 'Enviado!'  (FakeLLM resp 4 + 5)
"""
from __future__ import annotations

from uuid import uuid4

import ondeline_api.tools.buscar_cliente_sgp
import ondeline_api.tools.enviar_boleto

# Registrar tools (importa para auto-registro no registry global)
import ondeline_api.tools.transferir_para_humano  # noqa: F401
import pytest
import respx
from fakeredis.aioredis import FakeRedis
from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.adapters.llm.base import ChatResponse, ToolCall
from ondeline_api.adapters.llm.fakes import FakeLLMProvider
from ondeline_api.adapters.sgp.base import (
    ClienteSgp,
    Contrato,
    EnderecoSgp,
    Fatura,
)
from ondeline_api.adapters.sgp.fakes import FakeSgpProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.crypto import reset_caches as _reset_crypto_caches
from ondeline_api.db.models.business import (
    Cliente,
    Conversa,
    ConversaEstado,
    ConversaStatus,
)
from ondeline_api.db.models.business import (
    SgpProvider as SgpProviderEnum,
)
from ondeline_api.repositories.mensagem import MensagemRepo
from ondeline_api.services.llm_loop import run_turn
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.tools.context import ToolContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset_crypto() -> None:
    """Garante que os caches de crypto sao limpos antes do teste.

    test_crypto.py pode deixar caches em estado inconsistente (chaves erradas
    ou limpas) dependendo da ordem de execucao da suite.
    """
    _reset_crypto_caches()


BASE = "http://evo.test"
INST = "hermes-wa"


def _cli_sgp() -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="42",
        nome="Joao",
        cpf_cnpj="11122233344",
        contratos=[Contrato(id="100", plano="Premium", status="ativo", cidade="SP")],
        endereco=EnderecoSgp(cidade="SP"),
        titulos=[
            Fatura(
                id="T1", valor=110, vencimento="2026-05-15", status="aberto",
                link_pdf="https://sgp/T1.pdf", codigo_pix="PIX_T1"
            )
        ],
    )


async def test_fluxo_completo_oi_cpf_boleto(db_session: AsyncSession) -> None:
    cache_redis = FakeRedis(decode_responses=False)
    sgp_router = SgpRouter(
        primary=FakeSgpProvider(clientes={"11122233344": _cli_sgp()}),
        secondary=FakeSgpProvider(),
    )
    cache = SgpCacheService(
        redis=cache_redis,
        session=db_session,
        router=sgp_router,
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s",
        estado=ConversaEstado.AGUARDA_OPCAO, status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()

    # ── Turn 1: cliente 'oi' → bot pede CPF ──
    await MensagemRepo(db_session).insert_inbound_or_skip(
        conversa_id=conv.id, external_id=f"U1_{uuid4().hex[:8]}", text="Oi", media_type=None, media_url=None
    )
    await db_session.flush()
    fake1 = FakeLLMProvider(
        responses=[
            ChatResponse(
                content="Oi! Pode me passar seu CPF?",
                tool_calls=[], tokens_used=10, finish_reason="stop",
            )
        ]
    )
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "OUT_T1"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx = ToolContext(
            session=db_session, conversa=conv, cliente=None,
            evolution=adapter, sgp_router=sgp_router, sgp_cache=cache,
        )
        out1 = await run_turn(
            ctx=ctx, provider=fake1, model="Hermes-3",
            history_turns=12, max_iter=5, budget=None,
        )
        await adapter.aclose()
    assert out1.final_text is not None
    assert "CPF" in out1.final_text

    # ── Turn 2: cliente envia CPF → bot chama buscar_cliente_sgp → confirma ──
    await MensagemRepo(db_session).insert_inbound_or_skip(
        conversa_id=conv.id, external_id=f"U2_{uuid4().hex[:8]}", text="11122233344", media_type=None, media_url=None
    )
    await db_session.flush()
    fake2 = FakeLLMProvider(
        responses=[
            ChatResponse(
                content=None,
                tool_calls=[
                    ToolCall(id="c1", name="buscar_cliente_sgp", arguments={"cpf_cnpj": "11122233344"})
                ],
                tokens_used=20, finish_reason="tool_calls",
            ),
            ChatResponse(
                content="Encontrei voce, Joao! Plano Premium ativo.",
                tool_calls=[], tokens_used=15, finish_reason="stop",
            ),
        ]
    )
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "OUT_T2"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx2 = ToolContext(
            session=db_session, conversa=conv, cliente=None,
            evolution=adapter, sgp_router=sgp_router, sgp_cache=cache,
        )
        out2 = await run_turn(
            ctx=ctx2, provider=fake2, model="Hermes-3",
            history_turns=12, max_iter=5, budget=None,
        )
        await adapter.aclose()
    assert out2.final_text is not None
    assert "Joao" in out2.final_text or "Encontrei" in out2.final_text
    assert "buscar_cliente_sgp" in out2.tool_calls_made
    await db_session.refresh(conv)
    assert conv.cliente_id is not None

    # ── Turn 3: cliente pede boleto → tool enviar_boleto → bot confirma ──
    cliente_db = (
        await db_session.execute(select(Cliente).where(Cliente.id == conv.cliente_id))
    ).scalar_one()

    await MensagemRepo(db_session).insert_inbound_or_skip(
        conversa_id=conv.id, external_id=f"U3_{uuid4().hex[:8]}", text="manda boleto", media_type=None, media_url=None
    )
    await db_session.flush()
    fake3 = FakeLLMProvider(
        responses=[
            ChatResponse(
                content=None,
                tool_calls=[ToolCall(id="c2", name="enviar_boleto", arguments={"max_boletos": 1})],
                tokens_used=18, finish_reason="tool_calls",
            ),
            ChatResponse(
                content="Enviei! 📄 Confere ai.", tool_calls=[],
                tokens_used=12, finish_reason="stop",
            ),
        ]
    )
    with respx.mock(assert_all_called=True) as router:
        # 1 sendMedia (boleto) + 1 sendText (PIX) + 1 sendText (resposta final do bot)
        router.post(f"{BASE}/message/sendMedia/{INST}").respond(200, json={"ok": True})
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "OUT_T3"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx3 = ToolContext(
            session=db_session, conversa=conv, cliente=cliente_db,
            evolution=adapter, sgp_router=sgp_router, sgp_cache=cache,
        )
        out3 = await run_turn(
            ctx=ctx3, provider=fake3, model="Hermes-3",
            history_turns=12, max_iter=5, budget=None,
        )
        await adapter.aclose()
    assert "enviar_boleto" in out3.tool_calls_made
    assert out3.final_text is not None
    assert "Enviei" in out3.final_text
