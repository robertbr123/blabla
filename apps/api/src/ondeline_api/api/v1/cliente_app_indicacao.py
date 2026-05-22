"""Endpoint do app cliente pra obter o proprio codigo de indicacao.

Resolve `ClienteAppUser → Cliente` (SGP cache) via sgp_id ou cpf_hash,
reusa `IndicacaoRepo` pra gerar/recuperar codigo e retorna o link
WhatsApp pronto pra compartilhar.
"""
from __future__ import annotations

from urllib.parse import quote

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.config import get_settings
from ondeline_api.db.models.business import (
    Cliente,
    Config,
    IndicacaoUso,
)
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.deps import get_db
from ondeline_api.repositories.indicacao import IndicacaoRepo

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/cliente-app/indicacao",
    tags=["cliente-app:indicacao"],
)


class IndicacaoMeOut(BaseModel):
    codigo: str
    link_compartilhamento: str
    numero_empresa: str
    usos: int
    convertidos: int
    credito_aplicado: int  # quantos usos ja viraram credito (proxy do R$)


async def _resolve_cliente(
    user: ClienteAppUser, session: AsyncSession
) -> Cliente | None:
    """Encontra o Cliente (SGP cache) correspondente ao ClienteAppUser.

    Tenta sgp_id primeiro (match exato), depois cpf_hash.
    """
    if user.sgp_id:
        stmt = select(Cliente).where(Cliente.sgp_id == user.sgp_id).limit(1)
        c = (await session.execute(stmt)).scalar_one_or_none()
        if c is not None:
            return c
    stmt = select(Cliente).where(Cliente.cpf_hash == user.cpf_hash).limit(1)
    return (await session.execute(stmt)).scalar_one_or_none()


async def _numero_empresa(session: AsyncSession) -> str:
    """Le `indicacao.whatsapp_alvo` do config, fallback pra evolution_instance."""
    cfg = (
        await session.execute(
            select(Config).where(Config.key == "indicacao.whatsapp_alvo")
        )
    ).scalar_one_or_none()
    if cfg is not None:
        v = cfg.value
        if isinstance(v, dict) and "value" in v:
            v = v["value"]
        if isinstance(v, str) and v.strip():
            return "".join(c for c in v if c.isdigit())
    fallback = get_settings().evolution_instance or ""
    return "".join(c for c in fallback if c.isdigit())


@router.get("/meu", response_model=IndicacaoMeOut)
async def get_meu(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> IndicacaoMeOut:
    cliente = await _resolve_cliente(user, session)
    if cliente is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Sua conta ainda nao esta vinculada ao seu cadastro de cliente. "
                "Entre em contato com o suporte."
            ),
        )

    repo = IndicacaoRepo(session)
    ind = await repo.get_or_create_para_cliente(cliente.id)
    await session.commit()
    await session.refresh(ind)

    # Stats de usos.
    stmt_usos = select(IndicacaoUso).where(IndicacaoUso.indicacao_id == ind.id)
    usos = list((await session.execute(stmt_usos)).scalars())
    convertidos = sum(1 for u in usos if u.convertido_em is not None)
    creditados = sum(1 for u in usos if u.credito_aplicado_em is not None)

    numero = await _numero_empresa(session)
    texto = f"Indicado por {ind.codigo} — quero contratar"
    link = (
        f"https://wa.me/{numero}?text={quote(texto)}" if numero else ""
    )

    return IndicacaoMeOut(
        codigo=ind.codigo,
        link_compartilhamento=link,
        numero_empresa=numero,
        usos=len(usos),
        convertidos=convertidos,
        credito_aplicado=creditados,
    )
