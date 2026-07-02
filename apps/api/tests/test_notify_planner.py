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
from ondeline_api.db.models.business import Cliente
from ondeline_api.db.models.business import (
    SgpProvider as SgpProviderEnum,
)
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


async def test_schedule_vencimentos_apenas_no_dia_do_vencimento(db_session: AsyncSession) -> None:
    """Vencimento agenda SO no dia exato (D-0) — nao mais janela de 3 dias.

    Antes disparava todo dia em [hoje, hoje+3], repetindo a mensagem. Agora
    so no dia que vence, batendo com o gatilho da Meta `fatura_vencendo`.
    """
    cpf = "11122233344"
    titulos = [
        Fatura(id="T1", valor=100, vencimento=_today_str(0), status="aberto"),   # vence hoje → agenda
        Fatura(id="T2", valor=200, vencimento=_today_str(3), status="aberto"),   # 3 dias antes → nao
        Fatura(id="T3", valor=300, vencimento=_today_str(-1), status="aberto"),  # ja vencida → nao
    ]
    _, cache = await _make_cliente_with_titulos(db_session, cpf, titulos)
    count = await schedule_vencimentos(db_session, cache)
    assert count == 1


async def test_schedule_vencimentos_dedup(db_session: AsyncSession) -> None:
    cpf = "22233344455"
    titulos = [Fatura(id="T1", valor=100, vencimento=_today_str(0), status="aberto")]
    _, cache = await _make_cliente_with_titulos(db_session, cpf, titulos)
    a = await schedule_vencimentos(db_session, cache)
    b = await schedule_vencimentos(db_session, cache)
    assert a == 1
    assert b == 0


async def test_schedule_atrasos_agenda_para_1_5_15_dias(db_session: AsyncSession) -> None:
    cpf = "33344455566"
    titulos = [
        Fatura(id="T1", valor=100, vencimento=_today_str(-1), status="aberto"),   # D+1
        Fatura(id="T2", valor=200, vencimento=_today_str(-5), status="aberto"),   # D+5
        Fatura(id="T3", valor=300, vencimento=_today_str(-15), status="aberto"),  # D+15
        Fatura(id="T4", valor=400, vencimento=_today_str(-7), status="aberto"),   # nao é mais target
    ]
    _, cache = await _make_cliente_with_titulos(db_session, cpf, titulos)
    count = await schedule_atrasos(db_session, cache)
    assert count == 3


async def test_schedule_pagamentos_detecta_titulo_pago(db_session: AsyncSession) -> None:
    """Detecta fatura paga pelo `dataPagamento` recente — SEM depender de
    lembrete previo (early-payers tambem recebem o 'obrigado')."""
    cpf = "44455566677"
    titulos = [
        Fatura(
            id="T1", valor=100, vencimento=_today_str(-1),
            status="pago", data_pagamento=_today_str(0),
        )
    ]
    _, cache = await _make_cliente_with_titulos(db_session, cpf, titulos)
    count = await schedule_pagamentos(db_session, cache)
    assert count == 1


async def test_schedule_pagamentos_idempotente_por_titulo(db_session: AsyncSession) -> None:
    """Um titulo que ja teve PAGAMENTO agendado nao agenda de novo — senao o
    cliente receberia o 'obrigado' toda vez que o job roda."""
    cpf = "99988877766"
    titulos = [
        Fatura(
            id="T1", valor=100, vencimento=_today_str(-1),
            status="pago", data_pagamento=_today_str(0),
        )
    ]
    _, cache = await _make_cliente_with_titulos(db_session, cpf, titulos)
    a = await schedule_pagamentos(db_session, cache)
    b = await schedule_pagamentos(db_session, cache)
    assert a == 1
    assert b == 0


async def test_schedule_pagamentos_ignora_pagamento_antigo(db_session: AsyncSession) -> None:
    """Pagamento fora da janela (ha 30 dias) nao dispara — evita backlog."""
    cpf = "12312312312"
    titulos = [
        Fatura(
            id="T1", valor=100, vencimento=_today_str(-40),
            status="pago", data_pagamento=_today_str(-30),
        )
    ]
    _, cache = await _make_cliente_with_titulos(db_session, cpf, titulos)
    count = await schedule_pagamentos(db_session, cache)
    assert count == 0


async def test_schedule_pagamentos_ignora_aberto(db_session: AsyncSession) -> None:
    cpf = "55566677788"
    titulos = [Fatura(id="T1", valor=100, vencimento=_today_str(1), status="aberto")]
    _, cache = await _make_cliente_with_titulos(db_session, cpf, titulos)
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
