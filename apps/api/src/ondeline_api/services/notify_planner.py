"""Notification planner — decides who to notify (vencimento/atraso/pagamento).

Runs periodically via Celery beat. Doesn't send messages directly — schedules
Notificacao records that the notify_sender worker will process.
"""
from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.sgp.base import Fatura
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import (
    Cliente,
    Notificacao,
    NotificacaoStatus,
    NotificacaoTipo,
)
from ondeline_api.repositories.notificacao import NotificacaoRepo
from ondeline_api.services.sgp_cache import SgpCacheService

log = structlog.get_logger(__name__)


def _today_at(hour: int = 9) -> datetime:
    """Today's UTC date at the specified hour (default 09:00 UTC)."""
    now = datetime.now(tz=UTC)
    return datetime.combine(now.date(), time(hour=hour, tzinfo=UTC))


def _vence_em_dias(t: Fatura, days: int) -> bool:
    if not t.vencimento:
        return False
    try:
        v = datetime.fromisoformat(t.vencimento).date()
    except ValueError:
        return False
    return (v - datetime.now(tz=UTC).date()).days == days


def _vencimento_proximos_dias(t: Fatura, max_days: int) -> bool:
    if not t.vencimento:
        return False
    try:
        v = datetime.fromisoformat(t.vencimento).date()
    except ValueError:
        return False
    delta = (v - datetime.now(tz=UTC).date()).days
    return 0 <= delta <= max_days


async def _list_active_clientes(session: AsyncSession) -> list[Cliente]:
    stmt = select(Cliente).where(Cliente.deleted_at.is_(None))
    return list((await session.execute(stmt)).scalars().all())


async def schedule_vencimentos(
    session: AsyncSession,
    sgp_cache: SgpCacheService,
    *,
    look_ahead_days: int = 3,
) -> int:
    """For each active cliente, schedule VENCIMENTO notification for titulos
    with vencimento in [today, today+look_ahead_days].
    """
    repo = NotificacaoRepo(session)
    when = _today_at(9)
    count = 0
    for cliente in await _list_active_clientes(session):
        try:
            cpf = decrypt_pii(cliente.cpf_cnpj_encrypted)
        except Exception:
            continue
        cli_sgp = await sgp_cache.get_cliente(cpf)
        if cli_sgp is None:
            continue
        proximos = [
            t for t in cli_sgp.titulos
            if t.status == "aberto" and _vencimento_proximos_dias(t, look_ahead_days)
        ]
        if not proximos:
            continue
        n = await repo.schedule(
            cliente_id=cliente.id,
            tipo=NotificacaoTipo.VENCIMENTO,
            agendada_para=when,
            payload={
                "titulos": [
                    {"id": t.id, "valor": t.valor, "vencimento": t.vencimento}
                    for t in proximos
                ],
            },
        )
        if n is not None:
            count += 1
    log.info("planner.vencimentos.scheduled", count=count)
    return count


async def schedule_atrasos(
    session: AsyncSession,
    sgp_cache: SgpCacheService,
    *,
    targets: tuple[int, ...] = (1, 7, 15),
) -> int:
    """For each active cliente, schedule ATRASO notification for titulos
    overdue by exactly 1, 7, or 15 days.

    Each delay bucket gets a distinct agendada_para minute offset so the
    dedup key (cliente_id, tipo, agendada_para) remains unique across buckets.
    """
    repo = NotificacaoRepo(session)
    count = 0
    for cliente in await _list_active_clientes(session):
        try:
            cpf = decrypt_pii(cliente.cpf_cnpj_encrypted)
        except Exception:
            continue
        cli_sgp = await sgp_cache.get_cliente(cpf)
        if cli_sgp is None:
            continue
        for idx, d in enumerate(targets):
            atrasados = [
                t for t in cli_sgp.titulos
                if t.status == "aberto" and _vence_em_dias(t, -d)
            ]
            if not atrasados:
                continue
            # Offset by bucket index so dedup key is unique per (cliente, tipo, bucket).
            when = _today_at(10) + timedelta(minutes=idx)
            n = await repo.schedule(
                cliente_id=cliente.id,
                tipo=NotificacaoTipo.ATRASO,
                agendada_para=when,
                payload={
                    "dias_atraso": d,
                    "titulos": [
                        {"id": t.id, "valor": t.valor, "vencimento": t.vencimento}
                        for t in atrasados
                    ],
                },
            )
            if n is not None:
                count += 1
    log.info("planner.atrasos.scheduled", count=count)
    return count


async def schedule_pagamentos(
    session: AsyncSession,
    sgp_cache: SgpCacheService,
    *,
    look_back_days: int = 7,
) -> int:
    """Detect titulos that were 'aberto' (in recent notifications) but are
    now 'pago' in SGP. Schedule a PAGAMENTO thank-you notification.
    """
    repo = NotificacaoRepo(session)
    when = _today_at(11)
    cutoff = datetime.now(tz=UTC) - timedelta(days=look_back_days)
    stmt = (
        select(Notificacao)
        .where(
            and_(
                Notificacao.status == NotificacaoStatus.ENVIADA,
                Notificacao.tipo.in_([NotificacaoTipo.VENCIMENTO, NotificacaoTipo.ATRASO]),
                Notificacao.enviada_em >= cutoff,
            )
        )
    )
    recent = list((await session.execute(stmt)).scalars().all())
    seen_clientes = {n.cliente_id for n in recent}
    count = 0
    for cliente_id in seen_clientes:
        cliente = await session.get(Cliente, cliente_id)
        if cliente is None:
            continue
        try:
            cpf = decrypt_pii(cliente.cpf_cnpj_encrypted)
        except Exception:
            continue
        # invalidate cache to force fresh fetch
        await sgp_cache.invalidate(cpf)
        cli_sgp = await sgp_cache.get_cliente(cpf)
        if cli_sgp is None:
            continue
        # Look for previously-pending titulo IDs that are now pago
        pending_ids: set[str] = set()
        for n in recent:
            if n.cliente_id != cliente_id:
                continue
            for t in (n.payload or {}).get("titulos", []):
                pending_ids.add(str(t.get("id", "")))
        pagos_now = [
            t for t in cli_sgp.titulos
            if t.status == "pago" and t.id in pending_ids
        ]
        if not pagos_now:
            continue
        new_n = await repo.schedule(
            cliente_id=cliente_id,
            tipo=NotificacaoTipo.PAGAMENTO,
            agendada_para=when,
            payload={
                "titulos": [{"id": t.id, "valor": t.valor} for t in pagos_now],
            },
        )
        if new_n is not None:
            count += 1
    log.info("planner.pagamentos.scheduled", count=count)
    return count


async def schedule_followup_os(session: AsyncSession, *, minutes_after: int = 10) -> int:
    """Schedule OS_CONCLUIDA notification for OSes finished >=`minutes_after` ago.

    Default 10 minutos — janela curta pra captar o cliente ainda com a
    experiencia fresca na cabeca. Dedup do Notificacao garante 1 envio por OS.
    """
    from ondeline_api.db.models.business import OrdemServico, OsStatus

    now = datetime.now(tz=UTC)
    cutoff = now - timedelta(minutes=minutes_after)
    repo = NotificacaoRepo(session)
    stmt = select(OrdemServico).where(
        and_(
            OrdemServico.status == OsStatus.CONCLUIDA,
            OrdemServico.concluida_em <= cutoff,
        )
    )
    rows = list((await session.execute(stmt)).scalars().all())
    when = now + timedelta(minutes=1)
    count = 0
    for os_ in rows:
        if os_.cliente_id is None:
            continue
        n = await repo.schedule(
            cliente_id=os_.cliente_id,
            tipo=NotificacaoTipo.OS_CONCLUIDA,
            agendada_para=when,
            payload={
                "codigo": os_.codigo,
                "problema": os_.problema,
                "csat_request": True,
            },
        )
        if n is not None:
            count += 1
    log.info("planner.followup_os.scheduled", count=count)
    return count


async def broadcast_manutencao(session: AsyncSession) -> int:
    """For each Manutencao starting in next hour, schedule MANUTENCAO
    notification for each cliente in affected cidades.
    """
    from ondeline_api.db.models.business import Manutencao

    now = datetime.now(tz=UTC)
    cutoff = now + timedelta(hours=1)
    stmt = select(Manutencao).where(
        and_(
            Manutencao.notificar.is_(True),
            Manutencao.inicio_at >= now,
            Manutencao.inicio_at <= cutoff,
        )
    )
    manutencoes = list((await session.execute(stmt)).scalars().all())
    repo = NotificacaoRepo(session)
    count = 0
    for m in manutencoes:
        cidades = m.cidades or []
        if not cidades:
            continue
        for cidade in cidades:
            cli_stmt = select(Cliente).where(
                and_(
                    Cliente.cidade == cidade,
                    Cliente.deleted_at.is_(None),
                )
            )
            clientes = list((await session.execute(cli_stmt)).scalars().all())
            when = m.inicio_at - timedelta(minutes=30)
            for cliente in clientes:
                n = await repo.schedule(
                    cliente_id=cliente.id,
                    tipo=NotificacaoTipo.MANUTENCAO,
                    agendada_para=when,
                    payload={
                        "titulo": m.titulo,
                        "inicio_at": m.inicio_at.isoformat(),
                        "fim_at": m.fim_at.isoformat(),
                    },
                )
                if n is not None:
                    count += 1
    log.info("planner.manutencoes.scheduled", count=count)
    return count


async def lgpd_purge(session: AsyncSession) -> dict[str, int]:
    """Soft-delete Cliente and Conversa rows whose retention_until is past.

    Hard-delete rows that were soft-deleted >30 days ago (LGPD compliance:
    keep for 30d after the request, then erase).
    """
    from sqlalchemy import delete, update
    from sqlalchemy.engine import CursorResult

    from ondeline_api.db.models.business import Conversa as _Conversa

    now = datetime.now(tz=UTC)

    # Soft-delete Cliente rows
    cli_stmt = (
        update(Cliente)
        .where(
            and_(
                Cliente.retention_until.isnot(None),
                Cliente.retention_until < now,
                Cliente.deleted_at.is_(None),
            )
        )
        .values(deleted_at=now)
    )
    cli_result: CursorResult[tuple[()]] = await session.execute(cli_stmt)  # type: ignore[assignment]
    soft_clientes = cli_result.rowcount or 0

    # Soft-delete Conversa rows
    conv_stmt = (
        update(_Conversa)
        .where(
            and_(
                _Conversa.retention_until.isnot(None),
                _Conversa.retention_until < now,
                _Conversa.deleted_at.is_(None),
            )
        )
        .values(deleted_at=now)
    )
    conv_result: CursorResult[tuple[()]] = await session.execute(conv_stmt)  # type: ignore[assignment]
    soft_conversas = conv_result.rowcount or 0

    # Hard-delete (purge) rows soft-deleted > 30 days ago
    hard_cutoff = now - timedelta(days=30)
    hard_cli_stmt = delete(Cliente).where(
        and_(
            Cliente.deleted_at.isnot(None),
            Cliente.deleted_at < hard_cutoff,
        )
    )
    hard_cli: CursorResult[tuple[()]] = await session.execute(hard_cli_stmt)  # type: ignore[assignment]
    hard_cli_count = hard_cli.rowcount or 0

    hard_conv_stmt = delete(_Conversa).where(
        and_(
            _Conversa.deleted_at.isnot(None),
            _Conversa.deleted_at < hard_cutoff,
        )
    )
    hard_conv: CursorResult[tuple[()]] = await session.execute(hard_conv_stmt)  # type: ignore[assignment]
    hard_conv_count = hard_conv.rowcount or 0

    log.info(
        "lgpd.purge.completed",
        soft_clientes=soft_clientes,
        soft_conversas=soft_conversas,
        hard_clientes=hard_cli_count,
        hard_conversas=hard_conv_count,
    )
    return {
        "soft_clientes": soft_clientes,
        "soft_conversas": soft_conversas,
        "hard_clientes": hard_cli_count,
        "hard_conversas": hard_conv_count,
    }
