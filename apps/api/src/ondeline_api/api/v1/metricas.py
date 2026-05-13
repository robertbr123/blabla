"""Dashboard metrics endpoint."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.metrica import MetricasOut
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.business import (
    Conversa,
    ConversaStatus,
    Lead,
    LeadStatus,
    Mensagem,
    OrdemServico,
    OsStatus,
)
from ondeline_api.db.models.identity import Role
from ondeline_api.deps import get_db

router = APIRouter(prefix="/api/v1/metricas", tags=["metricas"])
_role_dep = Depends(require_role(Role.ATENDENTE, Role.ADMIN))


@router.get("", response_model=MetricasOut, dependencies=[_role_dep])
async def get_metricas(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MetricasOut:
    now = datetime.now(tz=UTC)
    yesterday = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Conversas em diferentes status
    aguardando = (
        await session.execute(
            select(func.count(Conversa.id)).where(
                Conversa.status == ConversaStatus.AGUARDANDO,
                Conversa.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    humano = (
        await session.execute(
            select(func.count(Conversa.id)).where(
                Conversa.status == ConversaStatus.HUMANO,
                Conversa.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    # Mensagens nas ultimas 24h
    msgs_24h = (
        await session.execute(
            select(func.count(Mensagem.id)).where(Mensagem.created_at >= yesterday)
        )
    ).scalar_one()

    # OS abertas (pendente ou em andamento)
    os_abertas = (
        await session.execute(
            select(func.count(OrdemServico.id)).where(
                OrdemServico.status.in_([OsStatus.PENDENTE, OsStatus.EM_ANDAMENTO])
            )
        )
    ).scalar_one()

    # OS concluidas 24h
    os_concluidas_24h = (
        await session.execute(
            select(func.count(OrdemServico.id)).where(
                OrdemServico.status == OsStatus.CONCLUIDA,
                OrdemServico.concluida_em >= yesterday,
            )
        )
    ).scalar_one()

    # CSAT medio ultimos 30d
    csat_avg = (
        await session.execute(
            select(func.avg(OrdemServico.csat)).where(
                OrdemServico.csat.isnot(None),
                OrdemServico.concluida_em >= month_ago,
            )
        )
    ).scalar_one()

    # Leads novos ultimos 7d
    leads_novos = (
        await session.execute(
            select(func.count(Lead.id)).where(
                Lead.status == LeadStatus.NOVO,
                Lead.created_at >= week_ago,
            )
        )
    ).scalar_one()

    return MetricasOut(
        conversas_aguardando=int(aguardando or 0),
        conversas_humano=int(humano or 0),
        msgs_24h=int(msgs_24h or 0),
        os_abertas=int(os_abertas or 0),
        os_concluidas_24h=int(os_concluidas_24h or 0),
        csat_avg_30d=float(csat_avg) if csat_avg is not None else None,
        leads_novos_7d=int(leads_novos or 0),
    )
