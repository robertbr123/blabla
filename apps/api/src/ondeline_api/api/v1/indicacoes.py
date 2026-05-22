"""GET/PATCH /api/v1/indicacoes — admin de indicações (F10)."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.indicacao import (
    IndicacaoOut,
    IndicacaoUsoMarcarConvertidoIn,
    IndicacaoUsoMarcarCreditoIn,
    IndicacaoUsoOut,
    RankingIndicadorOut,
)
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import (
    Cliente,
    Indicacao,
    IndicacaoUso,
    Lead,
)
from ondeline_api.db.models.identity import Role
from ondeline_api.deps import get_db
from ondeline_api.repositories.indicacao import IndicacaoRepo

router = APIRouter(prefix="/api/v1/indicacoes", tags=["indicacoes"])
_role_dep = Depends(require_role(Role.ATENDENTE, Role.ADMIN))
_admin_dep = Depends(require_role(Role.ADMIN))


def _decrypt(name_enc: str | None) -> str:
    if not name_enc:
        return ""
    try:
        return decrypt_pii(name_enc)
    except Exception:
        return ""


@router.get("", response_model=list[IndicacaoOut], dependencies=[_role_dep])
async def list_indicacoes(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[IndicacaoOut]:
    stmt = (
        select(Indicacao, Cliente.nome_encrypted)
        .join(Cliente, Cliente.id == Indicacao.cliente_indicador_id)
        .order_by(desc(Indicacao.criado_em))
    )
    out: list[IndicacaoOut] = []
    for ind, nome_enc in (await session.execute(stmt)).all():
        out.append(
            IndicacaoOut(
                id=ind.id,
                codigo=ind.codigo,
                cliente_indicador_id=ind.cliente_indicador_id,
                cliente_indicador_nome=_decrypt(nome_enc) or None,
                criado_em=ind.criado_em,
                expira_em=ind.expira_em,
                usos=ind.usos,
                ativo=ind.ativo,
            )
        )
    return out


@router.get(
    "/usos", response_model=list[IndicacaoUsoOut], dependencies=[_role_dep]
)
async def list_usos(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[IndicacaoUsoOut]:
    stmt = (
        select(
            IndicacaoUso,
            Indicacao.codigo,
            Lead.nome,
            Cliente.nome_encrypted,
        )
        .join(Indicacao, Indicacao.id == IndicacaoUso.indicacao_id)
        .outerjoin(Lead, Lead.id == IndicacaoUso.lead_id)
        .outerjoin(
            Cliente, Cliente.id == IndicacaoUso.cliente_indicado_id
        )
        .order_by(desc(IndicacaoUso.criado_em))
    )
    rows = (await session.execute(stmt)).all()
    out: list[IndicacaoUsoOut] = []
    for uso, codigo, lead_nome, cli_nome_enc in rows:
        out.append(
            IndicacaoUsoOut(
                id=uso.id,
                indicacao_id=uso.indicacao_id,
                indicacao_codigo=codigo,
                lead_id=uso.lead_id,
                lead_nome=lead_nome,
                cliente_indicado_id=uso.cliente_indicado_id,
                cliente_indicado_nome=_decrypt(cli_nome_enc) or None,
                criado_em=uso.criado_em,
                convertido_em=uso.convertido_em,
                credito_aplicado_em=uso.credito_aplicado_em,
                observacao=uso.observacao,
            )
        )
    return out


@router.post(
    "/usos/{uso_id}/converter",
    response_model=IndicacaoUsoOut,
    dependencies=[_admin_dep],
)
async def marcar_convertido(
    uso_id: UUID,
    body: IndicacaoUsoMarcarConvertidoIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> IndicacaoUsoOut:
    """Marca lead como convertido → cliente. Admin opcionalmente vincula cliente_id."""
    uso = (
        await session.execute(
            select(IndicacaoUso).where(IndicacaoUso.id == uso_id)
        )
    ).scalar_one_or_none()
    if uso is None:
        raise HTTPException(status_code=404, detail="uso not found")
    if uso.convertido_em is None:
        uso.convertido_em = datetime.now(tz=UTC)
    if body.cliente_indicado_id:
        uso.cliente_indicado_id = body.cliente_indicado_id
    if body.observacao:
        uso.observacao = (
            (uso.observacao + "\n" + body.observacao)
            if uso.observacao
            else body.observacao
        )
    await session.flush()

    # Re-fetch joined
    return await _hydrate_uso(session, uso.id)


@router.post(
    "/usos/{uso_id}/credito",
    response_model=IndicacaoUsoOut,
    dependencies=[_admin_dep],
)
async def marcar_credito_aplicado(
    uso_id: UUID,
    body: IndicacaoUsoMarcarCreditoIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> IndicacaoUsoOut:
    """Marca que admin já aplicou o crédito (R$ na fatura) no SGP."""
    uso = (
        await session.execute(
            select(IndicacaoUso).where(IndicacaoUso.id == uso_id)
        )
    ).scalar_one_or_none()
    if uso is None:
        raise HTTPException(status_code=404, detail="uso not found")
    if uso.convertido_em is None:
        raise HTTPException(
            status_code=400, detail="marque como convertido antes de aplicar crédito"
        )
    uso.credito_aplicado_em = datetime.now(tz=UTC)
    if body.observacao:
        uso.observacao = (
            (uso.observacao + "\n" + body.observacao)
            if uso.observacao
            else body.observacao
        )
    await session.flush()
    return await _hydrate_uso(session, uso.id)


@router.get(
    "/ranking",
    response_model=list[RankingIndicadorOut],
    dependencies=[_role_dep],
)
async def ranking(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[RankingIndicadorOut]:
    rows = await IndicacaoRepo(session).ranking_indicadores(limit=50)
    return [
        RankingIndicadorOut(
            cliente_id=c.id,
            cliente_nome=_decrypt(c.nome_encrypted) or "—",
            usos=usos,
            convertidos=conv,
        )
        for c, usos, conv in rows
    ]


@router.get("/stats", dependencies=[_role_dep])
async def stats(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, int]:
    """Stats agregadas pra dashboard: total shares via app + leads concretos."""
    total_shares = (
        await session.execute(select(func.coalesce(func.sum(Indicacao.shares_app), 0)))
    ).scalar_one()
    total_usos = (
        await session.execute(select(func.count(IndicacaoUso.id)))
    ).scalar_one()
    total_convertidos = (
        await session.execute(
            select(func.count(IndicacaoUso.id)).where(
                IndicacaoUso.convertido_em.isnot(None)
            )
        )
    ).scalar_one()
    return {
        "shares_app": int(total_shares or 0),
        "leads_whatsapp": int(total_usos or 0),
        "convertidos": int(total_convertidos or 0),
    }


async def _hydrate_uso(session: AsyncSession, uso_id: UUID) -> IndicacaoUsoOut:
    stmt = (
        select(
            IndicacaoUso,
            Indicacao.codigo,
            Lead.nome,
            Cliente.nome_encrypted,
        )
        .join(Indicacao, Indicacao.id == IndicacaoUso.indicacao_id)
        .outerjoin(Lead, Lead.id == IndicacaoUso.lead_id)
        .outerjoin(Cliente, Cliente.id == IndicacaoUso.cliente_indicado_id)
        .where(IndicacaoUso.id == uso_id)
    )
    row = (await session.execute(stmt)).one()
    uso, codigo, lead_nome, cli_nome_enc = row
    return IndicacaoUsoOut(
        id=uso.id,
        indicacao_id=uso.indicacao_id,
        indicacao_codigo=codigo,
        lead_id=uso.lead_id,
        lead_nome=lead_nome,
        cliente_indicado_id=uso.cliente_indicado_id,
        cliente_indicado_nome=_decrypt(cli_nome_enc) or None,
        criado_em=uso.criado_em,
        convertido_em=uso.convertido_em,
        credito_aplicado_em=uso.credito_aplicado_em,
        observacao=uso.observacao,
    )
