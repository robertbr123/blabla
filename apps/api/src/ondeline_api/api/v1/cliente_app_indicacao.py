"""Endpoint do app cliente pra obter o proprio codigo de indicacao.

Resolve `ClienteAppUser → Cliente` (SGP cache) via sgp_id ou cpf_hash,
reusa `IndicacaoRepo` pra gerar/recuperar codigo e retorna o link
WhatsApp pronto pra compartilhar.
"""
from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.config import get_settings
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import (
    Cliente,
    Config,
    IndicacaoUso,
)
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.deps import get_db
from ondeline_api.repositories.indicacao import IndicacaoRepo

log = structlog.get_logger(__name__)

# Milestone V1: hardcoded. Cliente atinge 3 convertidos -> 1 mes gratis
# (resgate manual pelo whatsapp, admin aplica no SGP). Mesmo padrao
# operacional do programa de fidelidade.
META_CONVERTIDOS = 3
RECOMPENSA_LABEL = "1 mês grátis"

router = APIRouter(
    prefix="/api/v1/cliente-app/indicacao",
    tags=["cliente-app:indicacao"],
)


class MilestoneOut(BaseModel):
    atingidos: int
    alvo: int
    recompensa: str
    atingido: bool


class IndicacaoMeOut(BaseModel):
    codigo: str
    link_compartilhamento: str
    numero_empresa: str
    usos: int
    convertidos: int
    credito_aplicado: int  # quantos usos ja viraram credito (proxy do R$)
    shares_app: int  # quantas vezes user tocou "Compartilhar" na tela in-app
    milestone: MilestoneOut


class TimelineItemOut(BaseModel):
    id: str
    nome_mascarado: str  # "M*** S***" ou "Lead recebido"
    status: str  # 'clique' | 'convertido' | 'creditado'
    criado_em: datetime
    convertido_em: datetime | None = None
    credito_aplicado_em: datetime | None = None


class TimelineOut(BaseModel):
    items: list[TimelineItemOut]


class IndicacaoShareOut(BaseModel):
    shares_app: int


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
        shares_app=ind.shares_app,
        milestone=MilestoneOut(
            atingidos=convertidos,
            alvo=META_CONVERTIDOS,
            recompensa=RECOMPENSA_LABEL,
            atingido=convertidos >= META_CONVERTIDOS,
        ),
    )


def _mask_nome(nome: str) -> str:
    """Transforma 'Maria Silva Santos' em 'M*** S***'.

    Pega primeira letra dos 2 primeiros tokens (>=2 chars). Quando o nome
    e muito curto ou vazio, devolve fallback.
    """
    if not nome or not nome.strip():
        return "Cliente"
    tokens = [t for t in nome.strip().split() if len(t) >= 2]
    if not tokens:
        return "Cliente"
    pieces = [f"{t[0].upper()}***" for t in tokens[:2]]
    return " ".join(pieces)


@router.get("/timeline", response_model=TimelineOut)
async def get_timeline(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> TimelineOut:
    """Ultimos 20 usos do codigo de indicacao do cliente atual.

    Devolve nomes mascarados (M*** S***) quando ha cliente_indicado_id
    resolvel. Senao, devolve "Lead recebido" (chegou no funil mas ainda
    nao virou cliente).
    """
    cliente = await _resolve_cliente(user, session)
    if cliente is None:
        return TimelineOut(items=[])

    repo = IndicacaoRepo(session)
    ind = await repo.get_or_create_para_cliente(cliente.id)

    stmt = (
        select(IndicacaoUso, Cliente)
        .outerjoin(Cliente, Cliente.id == IndicacaoUso.cliente_indicado_id)
        .where(IndicacaoUso.indicacao_id == ind.id)
        .order_by(IndicacaoUso.criado_em.desc())
        .limit(20)
    )
    rows = (await session.execute(stmt)).all()

    items: list[TimelineItemOut] = []
    for uso, cli in rows:
        if cli is not None:
            try:
                nome_claro = decrypt_pii(cli.nome_encrypted)
            except Exception:  # noqa: BLE001
                nome_claro = ""
            nome = _mask_nome(nome_claro)
        else:
            nome = "Lead recebido"

        if uso.credito_aplicado_em is not None:
            status = "creditado"
        elif uso.convertido_em is not None:
            status = "convertido"
        else:
            status = "clique"

        items.append(
            TimelineItemOut(
                id=str(uso.id),
                nome_mascarado=nome,
                status=status,
                criado_em=uso.criado_em,
                convertido_em=uso.convertido_em,
                credito_aplicado_em=uso.credito_aplicado_em,
            )
        )

    return TimelineOut(items=items)


@router.post("/share", response_model=IndicacaoShareOut)
async def registrar_share(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> IndicacaoShareOut:
    """Incrementa shares_app do codigo do cliente atual.

    Disparado quando o cliente toca "Compartilhar via WhatsApp" na tela
    in-app. Cria o codigo se ainda nao existir (idempotente com /meu).

    Tambem tenta completar a missao 'share_indicacao' do dia (Fase 3d) —
    falha silenciosa, nao bloqueia o share.
    """
    cliente = await _resolve_cliente(user, session)
    if cliente is None:
        raise HTTPException(
            status_code=409,
            detail="Conta nao vinculada ao cadastro de cliente.",
        )
    repo = IndicacaoRepo(session)
    ind = await repo.get_or_create_para_cliente(cliente.id)
    # Increment atomico.
    from sqlalchemy import update as _update

    from ondeline_api.db.models.business import Indicacao as _Ind
    from ondeline_api.services.missoes import completar as _completar_missao

    await session.execute(
        _update(_Ind)
        .where(_Ind.id == ind.id)
        .values(shares_app=_Ind.shares_app + 1)
    )
    await _completar_missao(session, user.id, "share_indicacao")
    await session.commit()
    await session.refresh(ind)
    return IndicacaoShareOut(shares_app=ind.shares_app)
