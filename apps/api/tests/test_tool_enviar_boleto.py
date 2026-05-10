"""Tool enviar_boleto — envia ate N boletos via Evolution mock."""
from __future__ import annotations

from uuid import uuid4

import pytest
import respx
from fakeredis.aioredis import FakeRedis
from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.adapters.sgp.base import (
    ClienteSgp,
    Contrato,
    EnderecoSgp,
    Fatura,
)
from ondeline_api.adapters.sgp.fakes import FakeSgpProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import (
    Cliente,
    Conversa,
    ConversaEstado,
    ConversaStatus,
)
from ondeline_api.db.models.business import (
    SgpProvider as SgpProviderEnum,
)
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.enviar_boleto import enviar_boleto
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


def _cli_sgp_com_2_faturas() -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="42",
        nome="X",
        cpf_cnpj="11122233344",
        contratos=[Contrato(id="100", plano="P", status="ativo", cidade="SP")],
        endereco=EnderecoSgp(cidade="SP"),
        titulos=[
            Fatura(
                id="T1", valor=110, vencimento="2026-05-15", status="aberto",
                link_pdf="https://sgp/T1.pdf", codigo_pix="PIXPIX_T1"
            ),
            Fatura(
                id="T2", valor=110, vencimento="2026-06-15", status="aberto",
                link_pdf="https://sgp/T2.pdf", codigo_pix="PIXPIX_T2"
            ),
        ],
    )


async def test_envia_2_boletos(db_session: AsyncSession) -> None:
    cli_sgp = _cli_sgp_com_2_faturas()
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=SgpRouter(
            primary=FakeSgpProvider(clientes={"11122233344": cli_sgp}),
            secondary=FakeSgpProvider(),
        ),
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("11122233344"),
        cpf_hash=hash_pii("11122233344"),
        nome_encrypted=encrypt_pii("X"),
        whatsapp="5511@s",
    )
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT
    )
    db_session.add_all([cliente, conv])
    await db_session.flush()

    BASE = "http://evo.test"
    INST = "hermes-wa"
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendMedia/{INST}").respond(200, json={"ok": True})
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "PIX_OUT"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx = ToolContext(
            session=db_session,
            conversa=conv,
            cliente=cliente,
            evolution=adapter,
            sgp_router=None,  # type: ignore[arg-type]
            sgp_cache=cache,
        )
        out = await enviar_boleto(ctx, max_boletos=2)
        await adapter.aclose()

    assert out["ok"] is True
    assert out["enviados"] == 2
    assert out["vencimentos"] == ["2026-05-15", "2026-06-15"]


async def test_sem_faturas_retorna_ok_zero(db_session: AsyncSession) -> None:
    cli_sgp = ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="9",
        nome="Y",
        cpf_cnpj="22233344455",
        contratos=[Contrato(id="200", plano="P", status="ativo", cidade="SP")],
        endereco=EnderecoSgp(cidade="SP"),
        titulos=[],
    )
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=SgpRouter(
            primary=FakeSgpProvider(clientes={"22233344455": cli_sgp}),
            secondary=FakeSgpProvider(),
        ),
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("22233344455"),
        cpf_hash=hash_pii("22233344455"),
        nome_encrypted=encrypt_pii("Y"),
        whatsapp="5512@s",
    )
    conv = Conversa(
        id=uuid4(), whatsapp="5512@s", estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT
    )
    db_session.add_all([cliente, conv])
    await db_session.flush()
    ctx = ToolContext(
        session=db_session,
        conversa=conv,
        cliente=cliente,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=cache,
    )
    out = await enviar_boleto(ctx)
    assert out == {"ok": True, "enviados": 0, "mensagem": "Sem faturas em aberto."}


async def test_sem_cliente_falha_grace(db_session: AsyncSession) -> None:
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT
    )
    db_session.add(conv)
    await db_session.flush()
    ctx = ToolContext(
        session=db_session,
        conversa=conv,
        cliente=None,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=None,  # type: ignore[arg-type]
    )
    out = await enviar_boleto(ctx)
    assert out["ok"] is False
