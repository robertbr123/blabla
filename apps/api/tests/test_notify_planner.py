"""Tests for notify_planner: schedule_vencimentos / atrasos / pagamentos."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
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
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import (
    Cliente,
    NotificacaoStatus,
    NotificacaoTipo,
)
from ondeline_api.db.models.business import (
    SgpProvider as SgpProviderEnum,
)
from ondeline_api.repositories.notificacao import NotificacaoRepo
from ondeline_api.services.notify_planner import (
    schedule_atrasos,
    schedule_pagamentos,
    schedule_vencimentos,
)
from ondeline_api.services.sgp_cache import SgpCacheService
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


def _today_str(offset_days: int = 0) -> str:
    return (datetime.now(tz=UTC).date() + timedelta(days=offset_days)).isoformat()


async def _make_cliente_with_titulos(
    db_session: AsyncSession,
    cpf: str,
    titulos: list[Fatura],
) -> tuple[Cliente, SgpCacheService]:
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii(cpf),
        cpf_hash=hash_pii(cpf),
        nome_encrypted=encrypt_pii("Test"),
        whatsapp=f"5511{uuid4().hex[:7]}@s.whatsapp.net",
    )
    db_session.add(cliente)
    await db_session.flush()
    cli_sgp = ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="42",
        nome="Test",
        cpf_cnpj=cpf,
        contratos=[Contrato(id="100", plano="P", status="ativo", cidade="SP")],
        endereco=EnderecoSgp(cidade="SP"),
        titulos=titulos,
    )
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=SgpRouter(
            primary=FakeSgpProvider(clientes={cpf: cli_sgp}),
            secondary=FakeSgpProvider(),
        ),
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    return cliente, cache


async def test_schedule_vencimentos_agenda_para_proximo_3_dias(db_session: AsyncSession) -> None:
    cpf = "11122233344"
    titulos = [
        Fatura(id="T1", valor=100, vencimento=_today_str(2), status="aberto"),
        Fatura(id="T2", valor=200, vencimento=_today_str(10), status="aberto"),  # too far
        Fatura(id="T3", valor=300, vencimento=_today_str(-1), status="aberto"),  # already past
    ]
    _, cache = await _make_cliente_with_titulos(db_session, cpf, titulos)
    count = await schedule_vencimentos(db_session, cache)
    assert count == 1


async def test_schedule_vencimentos_dedup(db_session: AsyncSession) -> None:
    cpf = "22233344455"
    titulos = [Fatura(id="T1", valor=100, vencimento=_today_str(1), status="aberto")]
    _, cache = await _make_cliente_with_titulos(db_session, cpf, titulos)
    a = await schedule_vencimentos(db_session, cache)
    b = await schedule_vencimentos(db_session, cache)
    assert a == 1
    assert b == 0


async def test_schedule_atrasos_agenda_para_1_7_15_dias(db_session: AsyncSession) -> None:
    cpf = "33344455566"
    titulos = [
        Fatura(id="T1", valor=100, vencimento=_today_str(-1), status="aberto"),
        Fatura(id="T2", valor=200, vencimento=_today_str(-7), status="aberto"),
        Fatura(id="T3", valor=300, vencimento=_today_str(-15), status="aberto"),
        Fatura(id="T4", valor=400, vencimento=_today_str(-3), status="aberto"),  # not target
    ]
    _, cache = await _make_cliente_with_titulos(db_session, cpf, titulos)
    count = await schedule_atrasos(db_session, cache)
    assert count == 3


async def test_schedule_pagamentos_detecta_titulo_pago(db_session: AsyncSession) -> None:
    cpf = "44455566677"
    # First, schedule + send a VENCIMENTO notification with titulo T1
    titulos = [Fatura(id="T1", valor=100, vencimento=_today_str(1), status="aberto")]
    cliente, cache = await _make_cliente_with_titulos(db_session, cpf, titulos)
    n = await NotificacaoRepo(db_session).schedule(
        cliente_id=cliente.id,
        tipo=NotificacaoTipo.VENCIMENTO,
        agendada_para=datetime.now(tz=UTC) - timedelta(hours=1),
        payload={"titulos": [{"id": "T1", "valor": 100, "vencimento": _today_str(1)}]},
    )
    assert n is not None
    # mark as ENVIADA
    n.status = NotificacaoStatus.ENVIADA
    n.enviada_em = datetime.now(tz=UTC) - timedelta(hours=1)
    await db_session.flush()

    # Now SGP says T1 is paid — replace cache router with paid version
    titulos_pagos = [Fatura(id="T1", valor=100, vencimento=_today_str(1), status="pago")]
    cli_sgp_paid = ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="42",
        nome="Test",
        cpf_cnpj=cpf,
        contratos=[Contrato(id="100", plano="P", status="ativo", cidade="SP")],
        endereco=EnderecoSgp(cidade="SP"),
        titulos=titulos_pagos,
    )
    cache._router = SgpRouter(
        primary=FakeSgpProvider(clientes={cpf: cli_sgp_paid}),
        secondary=FakeSgpProvider(),
    )

    count = await schedule_pagamentos(db_session, cache)
    assert count == 1


async def test_schedule_pagamentos_no_change_no_count(db_session: AsyncSession) -> None:
    cpf = "55566677788"
    titulos = [Fatura(id="T1", valor=100, vencimento=_today_str(1), status="aberto")]
    cliente, cache = await _make_cliente_with_titulos(db_session, cpf, titulos)
    n = await NotificacaoRepo(db_session).schedule(
        cliente_id=cliente.id,
        tipo=NotificacaoTipo.VENCIMENTO,
        agendada_para=datetime.now(tz=UTC) - timedelta(hours=1),
        payload={"titulos": [{"id": "T1", "valor": 100, "vencimento": _today_str(1)}]},
    )
    assert n is not None
    n.status = NotificacaoStatus.ENVIADA
    n.enviada_em = datetime.now(tz=UTC) - timedelta(hours=1)
    await db_session.flush()
    count = await schedule_pagamentos(db_session, cache)
    assert count == 0


async def test_cliente_sem_dados_sgp_skip(db_session: AsyncSession) -> None:
    cpf = "66677788899"
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii(cpf),
        cpf_hash=hash_pii(cpf),
        nome_encrypted=encrypt_pii("Anon"),
        whatsapp="5511@s.whatsapp.net",
    )
    db_session.add(cliente)
    await db_session.flush()
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=SgpRouter(primary=FakeSgpProvider(), secondary=FakeSgpProvider()),
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    count = await schedule_vencimentos(db_session, cache)
    # Won't crash; client just won't get notified
    assert count >= 0
