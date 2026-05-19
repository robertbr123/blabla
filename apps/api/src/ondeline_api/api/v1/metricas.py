"""Dashboard metrics endpoint."""
from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.metrica import (
    ComissaoConfigOut,
    MetricasOut,
    ProdutividadeResponse,
    ProdutividadeTecnicoOut,
    RankingTecnicoOut,
    TimeseriesOut,
    TimeseriesPontoOut,
)
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
    mes: str | None = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
) -> list[RankingTecnicoOut]:
    """Ranking de técnicos por OS concluídas no mês (formato: YYYY-MM)."""
    now = datetime.now(tz=UTC)
    if mes:
        year, month = int(mes.split("-")[0]), int(mes.split("-")[1])
    else:
        year, month = now.year, now.month

    inicio = datetime(year, month, 1, tzinfo=UTC)
    if month == 12:
        fim = datetime(year + 1, 1, 1, tzinfo=UTC)
    else:
        fim = datetime(year, month + 1, 1, tzinfo=UTC)

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
                & (OrdemServico.concluida_em < fim),
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
            tempo_medio_min=round(float(row.tempo_medio_min)) if row.tempo_medio_min is not None else None,
            ultima_os_em=row.ultima_os_em.isoformat() if row.ultima_os_em else None,
        )
        for row in rows
    ]


@router.get("/tecnicos/export", dependencies=[_role_dep])
async def export_ranking_tecnicos_csv(
    session: Annotated[AsyncSession, Depends(get_db)],
    mes: str | None = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
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
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Timeseries (tendencia diaria) ──────────────────────────────────


def _parse_days(days: int) -> int:
    # Clamp pra evitar query gigante.
    if days < 1:
        return 1
    if days > 365:
        return 365
    return days


async def _build_timeseries(
    session: AsyncSession, days: int
) -> list[TimeseriesPontoOut]:
    """Serie diaria dos ultimos N dias: msgs, os_concluidas, leads, csat_avg."""
    days = _parse_days(days)
    now = datetime.now(tz=UTC)
    # Dia local (UTC): trunca pra inicio do dia atual e volta N-1 dias.
    hoje = datetime(now.year, now.month, now.day, tzinfo=UTC)
    inicio = hoje - timedelta(days=days - 1)
    fim = hoje + timedelta(days=1)

    # Mensagens por dia (created_at).
    msgs_rows = (
        await session.execute(
            select(
                func.date_trunc("day", Mensagem.created_at).label("dia"),
                func.count(Mensagem.id).label("n"),
            )
            .where(Mensagem.created_at >= inicio, Mensagem.created_at < fim)
            .group_by("dia")
        )
    ).all()
    msgs_map: dict[str, int] = {
        r.dia.date().isoformat(): int(r.n or 0) for r in msgs_rows
    }

    # OS concluidas por dia.
    os_rows = (
        await session.execute(
            select(
                func.date_trunc("day", OrdemServico.concluida_em).label("dia"),
                func.count(OrdemServico.id).label("n"),
                func.avg(OrdemServico.csat).label("csat_avg"),
            )
            .where(
                OrdemServico.status == OsStatus.CONCLUIDA,
                OrdemServico.concluida_em >= inicio,
                OrdemServico.concluida_em < fim,
            )
            .group_by("dia")
        )
    ).all()
    os_map: dict[str, tuple[int, float | None]] = {
        r.dia.date().isoformat(): (
            int(r.n or 0),
            float(r.csat_avg) if r.csat_avg is not None else None,
        )
        for r in os_rows
    }

    # Leads novos por dia.
    leads_rows = (
        await session.execute(
            select(
                func.date_trunc("day", Lead.created_at).label("dia"),
                func.count(Lead.id).label("n"),
            )
            .where(Lead.created_at >= inicio, Lead.created_at < fim)
            .group_by("dia")
        )
    ).all()
    leads_map: dict[str, int] = {
        r.dia.date().isoformat(): int(r.n or 0) for r in leads_rows
    }

    pontos: list[TimeseriesPontoOut] = []
    for i in range(days):
        d = (inicio + timedelta(days=i)).date()
        key = d.isoformat()
        os_n, csat = os_map.get(key, (0, None))
        pontos.append(
            TimeseriesPontoOut(
                dia=key,
                msgs=msgs_map.get(key, 0),
                os_concluidas=os_n,
                leads_novos=leads_map.get(key, 0),
                csat_avg=round(csat, 2) if csat is not None else None,
            )
        )
    return pontos


@router.get("/timeseries", response_model=TimeseriesOut, dependencies=[_role_dep])
async def get_timeseries(
    session: Annotated[AsyncSession, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> TimeseriesOut:
    """Serie diaria de KPIs operacionais nos ultimos N dias (max 365)."""
    pontos = await _build_timeseries(session, days)
    return TimeseriesOut(days=_parse_days(days), pontos=pontos)


@router.get("/timeseries/export", dependencies=[_role_dep])
async def export_timeseries_csv(
    session: Annotated[AsyncSession, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> StreamingResponse:
    """Exporta timeseries diario como CSV."""
    pontos = await _build_timeseries(session, days)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Dia", "Mensagens", "OS Concluidas", "Leads Novos", "CSAT Medio"])
    for p in pontos:
        writer.writerow([
            p.dia,
            p.msgs,
            p.os_concluidas,
            p.leads_novos,
            f"{p.csat_avg:.2f}" if p.csat_avg is not None else "",
        ])
    filename = f"timeseries-{_parse_days(days)}d-{datetime.now(tz=UTC).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── F9 — Produtividade + comissão ──────────────────────────────────


_COMISSAO_KEYS = {
    "comissao.valor_por_os": 0.0,
    "comissao.bonus_csat_5": 0.0,
    "comissao.bonus_csat_4": 0.0,
}


async def _load_comissao_config(session: AsyncSession) -> dict[str, float]:
    """Carrega config de comissão (tabela `config`). Defaults se faltar."""
    from sqlalchemy import select as _sel

    from ondeline_api.db.models.business import Config as _Config

    rows = list(
        (
            await session.execute(
                _sel(_Config).where(_Config.key.in_(list(_COMISSAO_KEYS.keys())))
            )
        )
        .scalars()
        .all()
    )
    out = dict(_COMISSAO_KEYS)
    for row in rows:
        v: Any = row.value
        # Aceita {"value": 30} ou 30 direto.
        if isinstance(v, dict) and "value" in v:
            v = v["value"]
        try:
            out[row.key] = float(v)
        except (TypeError, ValueError):
            pass
    return out


@router.get(
    "/tecnicos/produtividade",
    dependencies=[_role_dep],
)
async def get_produtividade_tecnicos(
    session: Annotated[AsyncSession, Depends(get_db)],
    mes: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
) -> ProdutividadeResponse:
    """F9 — Ranking + cálculo de comissão por técnico.

    Comissao = (os_concluidas * valor_por_os) + (os_csat_5 * bonus_csat_5)
             + (os_csat_4 * bonus_csat_4)

    Configurar via tabela `config`:
      - comissao.valor_por_os
      - comissao.bonus_csat_5
      - comissao.bonus_csat_4
    """

    now = datetime.now(tz=UTC)
    if mes:
        year, month = int(mes.split("-")[0]), int(mes.split("-")[1])
    else:
        year, month = now.year, now.month

    inicio = datetime(year, month, 1, tzinfo=UTC)
    if month == 12:
        fim = datetime(year + 1, 1, 1, tzinfo=UTC)
    else:
        fim = datetime(year, month + 1, 1, tzinfo=UTC)

    cfg = await _load_comissao_config(session)
    valor_por_os = cfg["comissao.valor_por_os"]
    bonus_5 = cfg["comissao.bonus_csat_5"]
    bonus_4 = cfg["comissao.bonus_csat_4"]

    csat5_expr = func.sum(
        case((OrdemServico.csat == 5, 1), else_=0)
    ).label("os_csat_5")
    csat4_expr = func.sum(
        case((OrdemServico.csat == 4, 1), else_=0)
    ).label("os_csat_4")
    sem_csat_expr = func.sum(
        case((OrdemServico.csat.is_(None), 1), else_=0)
    ).label("os_sem_csat")

    rows = (
        await session.execute(
            select(
                Tecnico.id,
                Tecnico.nome,
                func.count(OrdemServico.id).label("os_concluidas"),
                csat5_expr,
                csat4_expr,
                sem_csat_expr,
                func.avg(OrdemServico.csat).label("csat_avg"),
                func.avg(
                    func.extract(
                        "epoch", OrdemServico.concluida_em - OrdemServico.criada_em
                    )
                    / 60
                ).label("tempo_medio_min"),
                func.max(OrdemServico.concluida_em).label("ultima_os_em"),
            )
            .outerjoin(
                OrdemServico,
                (OrdemServico.tecnico_id == Tecnico.id)
                & (OrdemServico.status == OsStatus.CONCLUIDA)
                & (OrdemServico.concluida_em >= inicio)
                & (OrdemServico.concluida_em < fim),
            )
            .where(Tecnico.ativo.is_(True))
            .group_by(Tecnico.id, Tecnico.nome)
            .order_by(func.count(OrdemServico.id).desc())
        )
    ).all()

    tecnicos_out: list[ProdutividadeTecnicoOut] = []
    for row in rows:
        os_conc = int(row.os_concluidas or 0)
        os_5 = int(row.os_csat_5 or 0)
        os_4 = int(row.os_csat_4 or 0)
        os_sem = int(row.os_sem_csat or 0)
        comissao_base = round(os_conc * valor_por_os, 2)
        comissao_bonus = round(os_5 * bonus_5 + os_4 * bonus_4, 2)
        comissao_total = round(comissao_base + comissao_bonus, 2)
        tecnicos_out.append(
            ProdutividadeTecnicoOut(
                tecnico_id=str(row.id),
                nome=row.nome,
                os_concluidas=os_conc,
                os_csat_5=os_5,
                os_csat_4=os_4,
                os_sem_csat=os_sem,
                csat_avg=(
                    round(float(row.csat_avg), 2)
                    if row.csat_avg is not None
                    else None
                ),
                tempo_medio_min=(
                    round(float(row.tempo_medio_min))
                    if row.tempo_medio_min is not None
                    else None
                ),
                ultima_os_em=(
                    row.ultima_os_em.isoformat() if row.ultima_os_em else None
                ),
                comissao_base=comissao_base,
                comissao_bonus=comissao_bonus,
                comissao_total=comissao_total,
            )
        )

    return ProdutividadeResponse(
        mes=f"{year:04d}-{month:02d}",
        config=ComissaoConfigOut(
            valor_por_os=valor_por_os,
            bonus_csat_5=bonus_5,
            bonus_csat_4=bonus_4,
        ),
        tecnicos=tecnicos_out,
    )
