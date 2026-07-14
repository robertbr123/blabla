"""Programa de fidelidade V1.

Pontos sao calculados sob demanda (sem tabela de saldo) baseando em:
- Tempo de casa: 10 pts * meses desde cliente_app_user.created_at,
  limitado aos ultimos MESES_JANELA (15) meses.
- Faturas pagas nos ultimos MESES_JANELA (15) meses: 50 pts se paga em dia
  (dias_atraso == 0), 10 pts se paga com atraso (dias_atraso > 0).

A janela de 15 meses evita que cliente antigo acumule pontos desde sempre
(50 pts/fatura por anos) e resgate "mes gratis" facil.

Recompensas sao hardcoded V1. Resgate cria pedido pendente em
cliente_app_fidelidade_resgates, admin aprova/aplica via dashboard
(integracao automatica com SGP fica pra V2).
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.crypto import decrypt_pii
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
PONTOS_FATURA_EM_DIA = 50
PONTOS_FATURA_ATRASADA = 10
# Janela de apuracao: so contam os ultimos 15 meses (tempo de casa + faturas).
MESES_JANELA = 15


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


def _cutoff_janela(now: datetime, meses: int) -> date:
    """Primeiro dia do mes 'meses' atras — corte inclusivo da janela de apuracao."""
    total = now.year * 12 + (now.month - 1) - meses
    ano, mes = divmod(total, 12)
    return date(ano, mes + 1, 1)


def _parse_venc(v: str) -> date | None:
    """Parse do vencimento SGP (YYYY-MM-DD). None se vazio/invalido."""
    if not v:
        return None
    try:
        return date.fromisoformat(v[:10])
    except ValueError:
        return None


async def _calcular_pontos(
    user: ClienteAppUser, session: AsyncSession
) -> tuple[int, BreakdownOut]:
    """Calcula pontos com base no estado atual do user + SGP."""
    from ondeline_api.api.v1.cliente_app_me import _sgp_cliente

    # Tempo no app — meses inteiros desde created_at, teto de MESES_JANELA.
    now = datetime.now(tz=UTC)
    delta_dias = (now - user.created_at).days
    meses_casa = min(max(0, delta_dias // 30), MESES_JANELA)
    pts_casa = meses_casa * PONTOS_POR_MES_CASA

    # Faturas pagas nos ultimos MESES_JANELA meses (por vencimento):
    # em dia (dias_atraso == 0) = 50 pts; com atraso (> 0) = 10 pts.
    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    cutoff = _cutoff_janela(now, MESES_JANELA)
    em_dia = 0
    atrasada = 0
    if sgp is not None:
        for t in sgp.titulos:
            if t.status != "pago":
                continue
            venc = _parse_venc(t.vencimento)
            if venc is None or venc < cutoff:
                continue
            if (t.dias_atraso or 0) > 0:
                atrasada += 1
            else:
                em_dia += 1
    pagas = em_dia + atrasada
    pts_pagas = (
        em_dia * PONTOS_FATURA_EM_DIA + atrasada * PONTOS_FATURA_ATRASADA
    )

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
    # Identificacao do cliente que pediu o resgate (antes so vinha o UUID).
    cliente_nome: str
    cliente_cpf_last4: str
    cliente_telefone: str | None = None


class AdminResgatePatch(BaseModel):
    status: str
    obs_admin: str | None = None


def _admin_resgate_out(
    r: ClienteAppFidelidadeResgate, user: ClienteAppUser | None
) -> AdminResgateOut:
    nome = ""
    cpf_last4 = ""
    telefone: str | None = None
    if user is not None:
        cpf_last4 = user.cpf_last4
        try:
            nome = decrypt_pii(user.nome_encrypted) if user.nome_encrypted else ""
        except Exception:
            nome = ""
        try:
            telefone = (
                decrypt_pii(user.telefone_encrypted) if user.telefone_encrypted else None
            )
        except Exception:
            telefone = None
    return AdminResgateOut(
        id=str(r.id),
        recompensa_slug=r.recompensa_slug,
        recompensa_label=r.recompensa_label,
        pontos_gastos=r.pontos_gastos,
        status=r.status,
        obs_admin=r.obs_admin,
        criado_em=r.criado_em.isoformat(),
        cliente_app_user_id=str(r.cliente_app_user_id),
        cliente_nome=nome,
        cliente_cpf_last4=cpf_last4,
        cliente_telefone=telefone,
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

    # Busca os usuarios em 1 query e monta o mapa pra decifrar nome/telefone.
    user_ids = {r.cliente_app_user_id for r in rows}
    users: dict[UUID, ClienteAppUser] = {}
    if user_ids:
        u_rows = (
            await session.execute(
                select(ClienteAppUser).where(ClienteAppUser.id.in_(user_ids))
            )
        ).scalars()
        users = {u.id: u for u in u_rows}

    return [_admin_resgate_out(r, users.get(r.cliente_app_user_id)) for r in rows]


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
    user = await session.get(ClienteAppUser, row.cliente_app_user_id)
    return _admin_resgate_out(row, user)
