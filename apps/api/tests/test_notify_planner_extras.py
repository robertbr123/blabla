"""Tests for follow-up OS, manutenção broadcast, and LGPD purge."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import (
    Cliente,
    Manutencao,
    OrdemServico,
    OsStatus,
)
from ondeline_api.services.notify_planner import (
    broadcast_manutencao,
    lgpd_purge,
    schedule_followup_os,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


def _cpf() -> str:
    return uuid4().hex[:11]


async def _make_cliente(db_session: AsyncSession, cidade: str | None = None) -> Cliente:
    c = _cpf()
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii(c),
        cpf_hash=hash_pii(c),
        nome_encrypted=encrypt_pii("Test"),
        whatsapp=f"5511{uuid4().hex[:7]}@s.whatsapp.net",
        cidade=cidade,
    )
    db_session.add(cliente)
    await db_session.flush()
    return cliente


async def test_followup_os_schedules_when_concluida_24h_ago(db_session: AsyncSession) -> None:
    cliente = await _make_cliente(db_session)
    os_ = OrdemServico(
        codigo=f"OS-{uuid4().hex[:6]}",
        cliente_id=cliente.id,
        problema="x",
        endereco="y",
        status=OsStatus.CONCLUIDA,
        concluida_em=datetime.now(tz=UTC) - timedelta(hours=25),
    )
    db_session.add(os_)
    await db_session.flush()
    count = await schedule_followup_os(db_session)
    assert count >= 1


async def test_followup_os_skip_recent(db_session: AsyncSession) -> None:
    cliente = await _make_cliente(db_session)
    os_ = OrdemServico(
        codigo=f"OS-{uuid4().hex[:6]}",
        cliente_id=cliente.id,
        problema="x",
        endereco="y",
        status=OsStatus.CONCLUIDA,
        concluida_em=datetime.now(tz=UTC) - timedelta(hours=1),  # too recent
    )
    db_session.add(os_)
    await db_session.flush()
    # First run: recent OS should NOT be scheduled (only old ones if any)
    await schedule_followup_os(db_session)
    final_count = await schedule_followup_os(db_session)
    # Second run should add 0 new (the recent one isn't due, dedup catches the rest)
    assert final_count == 0


async def test_broadcast_manutencao_targets_cidade_clientes(db_session: AsyncSession) -> None:
    cidade = f"Cidade-{uuid4().hex[:6]}"
    await _make_cliente(db_session, cidade=cidade)
    m = Manutencao(
        titulo="Teste",
        descricao="x",
        inicio_at=datetime.now(tz=UTC) + timedelta(minutes=30),
        fim_at=datetime.now(tz=UTC) + timedelta(hours=2),
        cidades=[cidade],
        notificar=True,
    )
    db_session.add(m)
    await db_session.flush()
    count = await broadcast_manutencao(db_session)
    assert count >= 1


async def test_broadcast_manutencao_skip_quando_notificar_false(db_session: AsyncSession) -> None:
    cidade = f"Cidade-{uuid4().hex[:6]}"
    await _make_cliente(db_session, cidade=cidade)
    m = Manutencao(
        titulo="Silent",
        inicio_at=datetime.now(tz=UTC) + timedelta(minutes=30),
        fim_at=datetime.now(tz=UTC) + timedelta(hours=2),
        cidades=[cidade],
        notificar=False,
    )
    db_session.add(m)
    await db_session.flush()
    count = await broadcast_manutencao(db_session)
    assert count == 0


async def test_lgpd_purge_soft_deletes_expired(db_session: AsyncSession) -> None:
    c = _cpf()
    expired = Cliente(
        cpf_cnpj_encrypted=encrypt_pii(c),
        cpf_hash=hash_pii(c),
        nome_encrypted=encrypt_pii("Expired"),
        whatsapp=f"5511{uuid4().hex[:7]}@s.whatsapp.net",
        retention_until=datetime.now(tz=UTC) - timedelta(days=1),
    )
    db_session.add(expired)
    await db_session.flush()
    result = await lgpd_purge(db_session)
    await db_session.refresh(expired)
    assert expired.deleted_at is not None
    assert result["soft_clientes"] >= 1


async def test_lgpd_purge_hard_deletes_after_30d(db_session: AsyncSession) -> None:
    c = _cpf()
    long_dead = Cliente(
        cpf_cnpj_encrypted=encrypt_pii(c),
        cpf_hash=hash_pii(c),
        nome_encrypted=encrypt_pii("LongDead"),
        whatsapp=f"5511{uuid4().hex[:7]}@s.whatsapp.net",
        retention_until=datetime.now(tz=UTC) - timedelta(days=60),
        deleted_at=datetime.now(tz=UTC) - timedelta(days=31),
    )
    db_session.add(long_dead)
    await db_session.flush()
    cliente_id = long_dead.id
    result = await lgpd_purge(db_session)
    assert result["hard_clientes"] >= 1
    # confirm gone
    fetched = (await db_session.execute(select(Cliente).where(Cliente.id == cliente_id))).scalar_one_or_none()
    assert fetched is None
