"""Programa de fidelidade V1.

Pontos sao calculados sob demanda (sem tabela de saldo) baseando em:
- Tempo de casa: 10 pts * meses desde cliente_app_user.created_at
- Faturas pagas: 50 pts * titulos do SGP com status != 'aberto'

Recompensas sao hardcoded V1. Resgate cria pedido pendente em
cliente_app_fidelidade_resgates, admin aprova/aplica via dashboard
(integracao automatica com SGP fica pra V2).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.cliente_app import (
    ClienteAppFidelidadeResgate,
    ClienteAppUser,
)
from ondeline_api.db.models.identity import Role
from ondeline_api.deps import get_db

# ════════ Configuracao das recompensas ════════

# Slug -> (label, pontos)
RECOMPENSAS: dict[str, tuple[str, int]] = {
    "desc5": ("5% off na próxima fatura", 500),
    "desc10": ("10% off na próxima fatura", 1000),
    "upgrade_temp": ("Upgrade de plano por 1 mês", 2000),
    "mes_gratis": ("1 mês grátis", 5000),
}

PONTOS_POR_MES_CASA = 10
PONTOS_POR_FATURA_PAGA = 50


# ════════ Schemas ════════


class BreakdownOut(BaseModel):
    tempo_casa_meses: int
    tempo_casa_pontos: int
    faturas_pagas_qtd: int
    faturas_pagas_pontos: int
    # Fase 3d — missoes (share/NPS/pagar_em_dia). Quando 0, app esconde.
    missoes_qtd: int = 0
    missoes_pontos: int = 0


class RecompensaOut(BaseModel):
    slug: str
    label: str
    pontos: int
    disponivel: bool


class ResgateOut(BaseModel):
    id: str
    recompensa_slug: str
    recompensa_label: str
    pontos_gastos: int
    status: str
    obs_admin: str | None
    criado_em: str


class FidelidadeOut(BaseModel):
    pontos_total: int
    pontos_disponiveis: int  # total - reservados em resgates pendentes/aprovados
    breakdown: BreakdownOut
    recompensas: list[RecompensaOut]
    resgates: list[ResgateOut]


class ResgatarIn(BaseModel):
    recompensa_slug: str


# ════════ Helpers ════════


async def _calcular_pontos(
    user: ClienteAppUser, session: AsyncSession
) -> tuple[int, BreakdownOut]:
    """Calcula pontos com base no estado atual do user + SGP."""
    from ondeline_api.api.v1.cliente_app_me import _sgp_cliente

    # Tempo no app — meses inteiros desde created_at.
    now = datetime.now(tz=UTC)
    delta_dias = (now - user.created_at).days
    meses_casa = max(0, delta_dias // 30)
    pts_casa = meses_casa * PONTOS_POR_MES_CASA

    # Faturas pagas (qualquer status diferente de 'aberto' no SGP).
    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    pagas = 0
    if sgp is not None:
        pagas = sum(1 for t in sgp.titulos if t.status and t.status != "aberto")
    pts_pagas = pagas * PONTOS_POR_FATURA_PAGA

    # Pontos das missoes (Fase 3d).
    from ondeline_api.services.missoes import calcular_pontos_missoes

    pts_missoes, contagem_missoes = await calcular_pontos_missoes(
        session, user
    )
    qtd_missoes = sum(contagem_missoes.values())

    total = pts_casa + pts_pagas + pts_missoes
    bd = BreakdownOut(
        tempo_casa_meses=meses_casa,
        tempo_casa_pontos=pts_casa,
        faturas_pagas_qtd=pagas,
        faturas_pagas_pontos=pts_pagas,
        missoes_qtd=qtd_missoes,
        missoes_pontos=pts_missoes,
    )
    return total, bd


async def _pontos_reservados(
    user_id: UUID, session: AsyncSession
) -> int:
    """Pontos ja comprometidos em resgates pendentes ou aprovados (nao aplicados)."""
    stmt = select(ClienteAppFidelidadeResgate).where(
        ClienteAppFidelidadeResgate.cliente_app_user_id == user_id,
        ClienteAppFidelidadeResgate.status.in_(["pendente", "aprovado"]),
    )
    rows = list((await session.execute(stmt)).scalars())
    return sum(r.pontos_gastos for r in rows)


def _resgate_out(r: ClienteAppFidelidadeResgate) -> ResgateOut:
    return ResgateOut(
        id=str(r.id),
        recompensa_slug=r.recompensa_slug,
        recompensa_label=r.recompensa_label,
        pontos_gastos=r.pontos_gastos,
        status=r.status,
        obs_admin=r.obs_admin,
        criado_em=r.criado_em.isoformat(),
    )


# ════════ Cliente router ════════

router = APIRouter(
    prefix="/api/v1/cliente-app/fidelidade",
    tags=["cliente-app:fidelidade"],
)


@router.get("", response_model=FidelidadeOut)
async def get_fidelidade(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> FidelidadeOut:
    total, breakdown = await _calcular_pontos(user, session)
    reservados = await _pontos_reservados(user.id, session)
    disponiveis = max(0, total - reservados)

    recompensas = [
        RecompensaOut(
            slug=slug,
            label=label,
            pontos=pontos,
            disponivel=disponiveis >= pontos,
        )
        for slug, (label, pontos) in RECOMPENSAS.items()
    ]

    resgates_stmt = (
        select(ClienteAppFidelidadeResgate)
        .where(ClienteAppFidelidadeResgate.cliente_app_user_id == user.id)
        .order_by(desc(ClienteAppFidelidadeResgate.criado_em))
        .limit(20)
    )
    resgates_rows = list((await session.execute(resgates_stmt)).scalars())

    return FidelidadeOut(
        pontos_total=total,
        pontos_disponiveis=disponiveis,
        breakdown=breakdown,
        recompensas=recompensas,
        resgates=[_resgate_out(r) for r in resgates_rows],
    )


@router.post(
    "/resgatar",
    response_model=ResgateOut,
    status_code=status.HTTP_201_CREATED,
)
async def resgatar(
    body: ResgatarIn,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> ResgateOut:
    if body.recompensa_slug not in RECOMPENSAS:
        raise HTTPException(status_code=400, detail="recompensa invalida")
    label, pontos = RECOMPENSAS[body.recompensa_slug]

    total, _ = await _calcular_pontos(user, session)
    reservados = await _pontos_reservados(user.id, session)
    disponiveis = total - reservados
    if disponiveis < pontos:
        raise HTTPException(
            status_code=409,
            detail=f"pontos insuficientes ({disponiveis} disponiveis, precisa de {pontos})",
        )

    row = ClienteAppFidelidadeResgate(
        cliente_app_user_id=user.id,
        recompensa_slug=body.recompensa_slug,
        recompensa_label=label,
        pontos_gastos=pontos,
        status="pendente",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _resgate_out(row)


# ════════ Admin router ════════

admin_router = APIRouter(
    prefix="/api/v1/admin/cliente-app-fidelidade",
    tags=["admin:cliente-app-fidelidade"],
)


class AdminResgateOut(ResgateOut):
    cliente_app_user_id: str


class AdminResgatePatch(BaseModel):
    status: str
    obs_admin: str | None = None


def _admin_resgate_out(r: ClienteAppFidelidadeResgate) -> AdminResgateOut:
    return AdminResgateOut(
        id=str(r.id),
        recompensa_slug=r.recompensa_slug,
        recompensa_label=r.recompensa_label,
        pontos_gastos=r.pontos_gastos,
        status=r.status,
        obs_admin=r.obs_admin,
        criado_em=r.criado_em.isoformat(),
        cliente_app_user_id=str(r.cliente_app_user_id),
    )


@admin_router.get(
    "",
    response_model=list[AdminResgateOut],
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_listar(
    session: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Annotated[str | None, None] = None,
) -> list[AdminResgateOut]:
    stmt = select(ClienteAppFidelidadeResgate).order_by(
        desc(ClienteAppFidelidadeResgate.criado_em)
    )
    if status_filter:
        stmt = stmt.where(ClienteAppFidelidadeResgate.status == status_filter)
    rows = list((await session.execute(stmt)).scalars())
    return [_admin_resgate_out(r) for r in rows]


@admin_router.patch(
    "/{resgate_id}",
    response_model=AdminResgateOut,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_patch(
    resgate_id: UUID,
    body: AdminResgatePatch,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminResgateOut:
    if body.status not in {"pendente", "aprovado", "aplicado", "rejeitado"}:
        raise HTTPException(status_code=400, detail="status invalido")
    row = await session.get(ClienteAppFidelidadeResgate, resgate_id)
    if row is None:
        raise HTTPException(status_code=404, detail="resgate nao encontrado")
    row.status = body.status
    if body.obs_admin is not None:
        row.obs_admin = body.obs_admin
    await session.commit()
    await session.refresh(row)
    return _admin_resgate_out(row)
