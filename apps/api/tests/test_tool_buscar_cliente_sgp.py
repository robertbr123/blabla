"""Tool buscar_cliente_sgp — usa SgpCacheService + ClienteRepo + vincula conversa."""
from __future__ import annotations

from uuid import uuid4

import pytest
from fakeredis.aioredis import FakeRedis
from ondeline_api.adapters.sgp.base import (
    ClienteSgp,
    Contrato,
    EnderecoSgp,
    Fatura,
)
from ondeline_api.adapters.sgp.fakes import FakeSgpProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
)
from ondeline_api.db.models.business import (
    SgpProvider as SgpProviderEnum,
)
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.tools.buscar_cliente_sgp import buscar_cliente_sgp
from ondeline_api.tools.context import ToolContext
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_encontra_e_vincula_conversa(db_session: AsyncSession) -> None:
    cli = ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="42",
        nome="Joao",
        cpf_cnpj="11122233344",
        contratos=[Contrato(id="100", plano="Premium", status="ativo", cidade="SP")],
        endereco=EnderecoSgp(cidade="SP"),
        titulos=[Fatura(id="T1", valor=110, vencimento="2026-05-15", status="aberto")],
    )
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=SgpRouter(
            primary=FakeSgpProvider(clientes={"11122233344": cli}),
            secondary=FakeSgpProvider(),
        ),
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    conv = Conversa(
        id=uuid4(),
        whatsapp="5511@s",
        estado=ConversaEstado.CLIENTE_CPF,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()

    ctx = ToolContext(
        session=db_session,
        conversa=conv,
        cliente=None,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=cache,
    )
    out = await buscar_cliente_sgp(ctx, cpf_cnpj="111.222.333-44")
    assert out["encontrado"] is True
    assert out["nome"] == "Joao"
    assert out["plano"] == "Premium"
    assert out["faturas"]["abertos"] == 1

    # vinculou cliente_id
    await db_session.flush()
    assert conv.cliente_id is not None


async def test_retorna_proximo_vencimento_e_valor(db_session: AsyncSession) -> None:
    cli = ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="42",
        nome="Joao",
        cpf_cnpj="11122233344",
        contratos=[Contrato(id="100", plano="P", status="ativo", cidade="SP")],
        endereco=EnderecoSgp(cidade="SP"),
        titulos=[
            Fatura(id="T1", valor=99.90, vencimento="2026-06-15", status="aberto"),
            Fatura(id="T2", valor=110, vencimento="2026-05-15", status="aberto", dias_atraso=2),
        ],
    )
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=SgpRouter(
            primary=FakeSgpProvider(clientes={"11122233344": cli}),
            secondary=FakeSgpProvider(),
        ),
        ttl_cliente=3600, ttl_negativo=300,
    )
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s",
        estado=ConversaEstado.CLIENTE_CPF, status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()
    ctx = ToolContext(
        session=db_session, conversa=conv, cliente=None,
        evolution=None, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
    )
    out = await buscar_cliente_sgp(ctx, cpf_cnpj="11122233344")
    # mais antiga em atraso (T2, vencimento 2026-05-15)
    assert out["faturas"]["proximo_vencimento"] == "2026-05-15"
    assert out["faturas"]["proximo_valor"] == 110
    assert out["faturas"]["atrasados"] == 1
    assert out["suspenso"] is False
    assert "contratos" not in out  # so 1 contrato


async def test_cliente_suspenso(db_session: AsyncSession) -> None:
    cli = ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="9", nome="Y", cpf_cnpj="22233344455",
        contratos=[Contrato(id="200", plano="P", status="Suspenso por inadimplencia", cidade="SP")],
        endereco=EnderecoSgp(cidade="SP"),
        titulos=[],
    )
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=SgpRouter(
            primary=FakeSgpProvider(clientes={"22233344455": cli}),
            secondary=FakeSgpProvider(),
        ),
        ttl_cliente=3600, ttl_negativo=300,
    )
    conv = Conversa(
        id=uuid4(), whatsapp="5512@s",
        estado=ConversaEstado.CLIENTE_CPF, status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()
    ctx = ToolContext(
        session=db_session, conversa=conv, cliente=None,
        evolution=None, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
    )
    out = await buscar_cliente_sgp(ctx, cpf_cnpj="22233344455")
    assert out["suspenso"] is True


async def test_multiplos_contratos_retorna_lista(db_session: AsyncSession) -> None:
    cli = ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="7", nome="Multi", cpf_cnpj="33344455566",
        contratos=[
            Contrato(id="C1", plano="Plano Casa", status="ativo", cidade="SP"),
            Contrato(id="C2", plano="Plano Trabalho", status="ativo", cidade="Rio"),
        ],
        endereco=EnderecoSgp(cidade="SP"),
        titulos=[],
    )
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=SgpRouter(
            primary=FakeSgpProvider(clientes={"33344455566": cli}),
            secondary=FakeSgpProvider(),
        ),
        ttl_cliente=3600, ttl_negativo=300,
    )
    conv = Conversa(
        id=uuid4(), whatsapp="5513@s",
        estado=ConversaEstado.CLIENTE_CPF, status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()
    ctx = ToolContext(
        session=db_session, conversa=conv, cliente=None,
        evolution=None, sgp_router=None, sgp_cache=cache,  # type: ignore[arg-type]
    )
    out = await buscar_cliente_sgp(ctx, cpf_cnpj="33344455566")
    assert out.get("multiplos_contratos") is True
    assert len(out["contratos"]) == 2
    assert out["contratos"][0]["plano"] == "Plano Casa"
    assert out["contratos"][1]["plano"] == "Plano Trabalho"


async def test_nao_encontrado(db_session: AsyncSession) -> None:
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=SgpRouter(primary=FakeSgpProvider(), secondary=FakeSgpProvider()),
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.CLIENTE_CPF, status=ConversaStatus.BOT
    )
    db_session.add(conv)
    await db_session.flush()
    ctx = ToolContext(
        session=db_session,
        conversa=conv,
        cliente=None,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=cache,
    )
    out = await buscar_cliente_sgp(ctx, cpf_cnpj="00000000000")
    assert out == {"encontrado": False}
