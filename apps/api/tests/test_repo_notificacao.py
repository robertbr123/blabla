"""NotificacaoRepo: schedule + dedup + list_due + lifecycle."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import Cliente, NotificacaoStatus, NotificacaoTipo
from ondeline_api.repositories.notificacao import NotificacaoRepo
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def _make_cliente(db_session: AsyncSession) -> Cliente:
    cpf = uuid4().hex[:11]
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii(cpf),
        cpf_hash=hash_pii(cpf),
        nome_encrypted=encrypt_pii("Test"),
        whatsapp=f"5511{uuid4().hex[:7]}@s.whatsapp.net",
    )
    db_session.add(cliente)
    await db_session.flush()
    return cliente


async def test_schedule_creates_pending(db_session: AsyncSession) -> None:
    cliente = await _make_cliente(db_session)
    repo = NotificacaoRepo(db_session)
    when = datetime.now(tz=UTC) + timedelta(hours=1)
    n = await repo.schedule(
        cliente_id=cliente.id,
        tipo=NotificacaoTipo.VENCIMENTO,
        agendada_para=when,
        payload={"valor": 110.0},
    )
    assert n is not None
    assert n.status == NotificacaoStatus.PENDENTE
    assert n.tentativas == 0


async def test_schedule_dedup_returns_none(db_session: AsyncSession) -> None:
    cliente = await _make_cliente(db_session)
    repo = NotificacaoRepo(db_session)
    when = datetime.now(tz=UTC) + timedelta(hours=1)
    a = await repo.schedule(
        cliente_id=cliente.id, tipo=NotificacaoTipo.VENCIMENTO,
        agendada_para=when, payload={},
    )
    b = await repo.schedule(
        cliente_id=cliente.id, tipo=NotificacaoTipo.VENCIMENTO,
        agendada_para=when, payload={},
    )
    assert a is not None
    assert b is None


async def test_list_due_filters_by_status_and_date(db_session: AsyncSession) -> None:
    cliente = await _make_cliente(db_session)
    repo = NotificacaoRepo(db_session)
    now = datetime.now(tz=UTC)
    # Past one (due)
    a = await repo.schedule(
        cliente_id=cliente.id, tipo=NotificacaoTipo.VENCIMENTO,
        agendada_para=now - timedelta(minutes=5), payload={"x": "due"},
    )
    # Future one (not due)
    b = await repo.schedule(
        cliente_id=cliente.id, tipo=NotificacaoTipo.ATRASO,
        agendada_para=now + timedelta(hours=1), payload={"x": "future"},
    )
    assert a is not None and b is not None
    due = await repo.list_due(now=now)
    ids = [n.id for n in due]
    assert a.id in ids
    assert b.id not in ids


async def test_mark_sent_updates_status_and_timestamp(db_session: AsyncSession) -> None:
    cliente = await _make_cliente(db_session)
    repo = NotificacaoRepo(db_session)
    n = await repo.schedule(
        cliente_id=cliente.id, tipo=NotificacaoTipo.VENCIMENTO,
        agendada_para=datetime.now(tz=UTC), payload={},
    )
    assert n is not None
    await repo.mark_sent(n)
    assert n.status == NotificacaoStatus.ENVIADA
    assert n.enviada_em is not None


async def test_mark_failed_third_attempt_marks_falha(db_session: AsyncSession) -> None:
    cliente = await _make_cliente(db_session)
    repo = NotificacaoRepo(db_session)
    n = await repo.schedule(
        cliente_id=cliente.id, tipo=NotificacaoTipo.ATRASO,
        agendada_para=datetime.now(tz=UTC), payload={},
    )
    assert n is not None
    await repo.mark_failed(n)
    assert n.status == NotificacaoStatus.PENDENTE
    assert n.tentativas == 1
    await repo.mark_failed(n)
    assert n.status == NotificacaoStatus.PENDENTE
    assert n.tentativas == 2
    await repo.mark_failed(n)
    assert n.status == NotificacaoStatus.FALHA  # type: ignore[comparison-overlap]
    assert n.tentativas == 3
