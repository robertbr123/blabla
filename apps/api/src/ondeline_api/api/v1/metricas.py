"""Dashboard metrics endpoint."""
from __future__ import annotations

import csv
import io
from calendar import monthrange
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.metrica import MetricasOut, RankingTecnicoOut
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.business import (
    Conversa,
    ConversaStatus,
    Lead,
    LeadStatus,
    Mensagem,
    OrdemServico,
    OsStatus,
    Tecnico,
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


@router.get("/tecnicos", response_model=list[RankingTecnicoOut], dependencies=[_role_dep])
async def get_ranking_tecnicos(
    session: Annotated[AsyncSession, Depends(get_db)],
    mes: str | None = None,
) -> list[RankingTecnicoOut]:
    """Ranking de técnicos por OS concluídas no mês (formato: YYYY-MM)."""
    now = datetime.now(tz=UTC)
    if mes:
        year, month = int(mes.split("-")[0]), int(mes.split("-")[1])
    else:
        year, month = now.year, now.month

    inicio = datetime(year, month, 1, tzinfo=UTC)
    last_day = monthrange(year, month)[1]
    fim = datetime(year, month, last_day, 23, 59, 59, tzinfo=UTC)

    rows = (
        await session.execute(
            select(
                Tecnico.id,
                Tecnico.nome,
                func.count(OrdemServico.id).label("os_concluidas"),
                func.avg(OrdemServico.csat).label("csat_avg"),
                func.avg(
                    func.extract("epoch", OrdemServico.concluida_em - OrdemServico.criada_em) / 60
                ).label("tempo_medio_min"),
                func.max(OrdemServico.concluida_em).label("ultima_os_em"),
            )
            .outerjoin(
                OrdemServico,
                (OrdemServico.tecnico_id == Tecnico.id)
                & (OrdemServico.status == OsStatus.CONCLUIDA)
                & (OrdemServico.concluida_em >= inicio)
                & (OrdemServico.concluida_em <= fim),
            )
            .where(Tecnico.ativo.is_(True))
            .group_by(Tecnico.id, Tecnico.nome)
            .order_by(func.count(OrdemServico.id).desc())
        )
    ).all()

    return [
        RankingTecnicoOut(
            tecnico_id=str(row.id),
            nome=row.nome,
            os_concluidas=int(row.os_concluidas or 0),
            csat_avg=round(float(row.csat_avg), 2) if row.csat_avg is not None else None,
            tempo_medio_min=int(row.tempo_medio_min) if row.tempo_medio_min is not None else None,
            ultima_os_em=row.ultima_os_em.isoformat() if row.ultima_os_em else None,
        )
        for row in rows
    ]


@router.get("/tecnicos/export", dependencies=[_role_dep])
async def export_ranking_tecnicos_csv(
    session: Annotated[AsyncSession, Depends(get_db)],
    mes: str | None = None,
) -> StreamingResponse:
    """Exporta ranking de técnicos como CSV para download."""
    ranking = await get_ranking_tecnicos(session=session, mes=mes)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Tecnico", "OS Concluidas", "CSAT Medio", "Tempo Medio (min)", "Mes"])
    mes_label = mes or datetime.now(tz=UTC).strftime("%Y-%m")
    for r in ranking:
        writer.writerow([
            r.nome,
            r.os_concluidas,
            f"{r.csat_avg:.2f}" if r.csat_avg is not None else "",
            str(r.tempo_medio_min) if r.tempo_medio_min is not None else "",
            mes_label,
        ])

    filename = f"ranking-tecnicos-{mes_label}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
