"""Card do dia — rotaciona conteudo na Home do app cliente.

Backend escolhe 1 card ativo por dia/usuario via hash deterministico:
mesmo (user_id, data) sempre devolve o mesmo card. Quando o dia vira,
proximo card da lista. Pra cliente novo, sempre comeca de um indice
diferente (hash inclui user_id).
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import asc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.cliente_app import (
    ClienteAppCardDia,
    ClienteAppUser,
)
from ondeline_api.db.models.identity import Role
from ondeline_api.deps import get_db

router = APIRouter(
    prefix="/api/v1/cliente-app",
    tags=["cliente-app:card-dia"],
)


class CardDiaOut(BaseModel):
    id: str
    slug: str
    titulo: str
    corpo: str
    cta_label: str
    cta_action: str
    icon: str | None = None
    gradient_from: str | None = None
    gradient_to: str | None = None


@router.get("/card-dia", response_model=CardDiaOut | None)
async def get_card_dia(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> CardDiaOut | None:
    stmt = (
        select(ClienteAppCardDia)
        .where(ClienteAppCardDia.ativo.is_(True))
        .order_by(ClienteAppCardDia.criado_em)
    )
    cards = list((await session.execute(stmt)).scalars())
    if not cards:
        return None

    hoje = datetime.now(tz=UTC).date().isoformat()
    key = f"{user.id}:{hoje}".encode()
    idx = int.from_bytes(hashlib.sha256(key).digest()[:4], "big") % len(cards)
    c = cards[idx]
    return CardDiaOut(
        id=str(c.id),
        slug=c.slug,
        titulo=c.titulo,
        corpo=c.corpo,
        cta_label=c.cta_label,
        cta_action=c.cta_action,
        icon=c.icon,
        gradient_from=c.gradient_from,
        gradient_to=c.gradient_to,
    )


# ════════════ Admin router ════════════

admin_router = APIRouter(
    prefix="/api/v1/admin/cliente-app-cards-dia",
    tags=["admin:cliente-app-cards-dia"],
)


class CardDiaIn(BaseModel):
    slug: str = Field(min_length=1, max_length=48)
    titulo: str = Field(min_length=1, max_length=120)
    corpo: str = Field(min_length=1, max_length=2000)
    cta_label: str = Field(default="Saiba mais", max_length=48)
    cta_action: str = Field(default="info", max_length=255)
    icon: str | None = Field(default=None, max_length=48)
    gradient_from: str | None = Field(default=None, max_length=8)
    gradient_to: str | None = Field(default=None, max_length=8)
    ativo: bool = True


class CardDiaPatch(BaseModel):
    slug: str | None = Field(default=None, max_length=48)
    titulo: str | None = Field(default=None, max_length=120)
    corpo: str | None = Field(default=None, max_length=2000)
    cta_label: str | None = Field(default=None, max_length=48)
    cta_action: str | None = Field(default=None, max_length=255)
    icon: str | None = Field(default=None, max_length=48)
    gradient_from: str | None = Field(default=None, max_length=8)
    gradient_to: str | None = Field(default=None, max_length=8)
    ativo: bool | None = None


class AdminCardDiaOut(CardDiaOut):
    ativo: bool
    criado_em: str
    atualizado_em: str


def _admin_out(c: ClienteAppCardDia) -> AdminCardDiaOut:
    return AdminCardDiaOut(
        id=str(c.id),
        slug=c.slug,
        titulo=c.titulo,
        corpo=c.corpo,
        cta_label=c.cta_label,
        cta_action=c.cta_action,
        icon=c.icon,
        gradient_from=c.gradient_from,
        gradient_to=c.gradient_to,
        ativo=c.ativo,
        criado_em=c.criado_em.isoformat(),
        atualizado_em=c.atualizado_em.isoformat(),
    )


@admin_router.get(
    "",
    response_model=list[AdminCardDiaOut],
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_listar(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[AdminCardDiaOut]:
    stmt = select(ClienteAppCardDia).order_by(
        asc(ClienteAppCardDia.criado_em),
    )
    rows = list((await session.execute(stmt)).scalars())
    return [_admin_out(r) for r in rows]


@admin_router.post(
    "",
    response_model=AdminCardDiaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_criar(
    body: CardDiaIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminCardDiaOut:
    row = ClienteAppCardDia(
        slug=body.slug,
        titulo=body.titulo,
        corpo=body.corpo,
        cta_label=body.cta_label,
        cta_action=body.cta_action,
        icon=body.icon,
        gradient_from=body.gradient_from,
        gradient_to=body.gradient_to,
        ativo=body.ativo,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="slug ja existe",
        ) from e
    await session.refresh(row)
    return _admin_out(row)


@admin_router.patch(
    "/{card_id}",
    response_model=AdminCardDiaOut,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_patch(
    card_id: UUID,
    body: CardDiaPatch,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminCardDiaOut:
    row = await session.get(ClienteAppCardDia, card_id)
    if row is None:
        raise HTTPException(status_code=404, detail="card nao encontrado")
    if body.slug is not None:
        row.slug = body.slug
    if body.titulo is not None:
        row.titulo = body.titulo
    if body.corpo is not None:
        row.corpo = body.corpo
    if body.cta_label is not None:
        row.cta_label = body.cta_label
    if body.cta_action is not None:
        row.cta_action = body.cta_action
    if body.icon is not None:
        row.icon = body.icon
    if body.gradient_from is not None:
        row.gradient_from = body.gradient_from
    if body.gradient_to is not None:
        row.gradient_to = body.gradient_to
    if body.ativo is not None:
        row.ativo = body.ativo
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="slug ja existe",
        ) from e
    await session.refresh(row)
    return _admin_out(row)


@admin_router.delete(
    "/{card_id}",
    status_code=204,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_deletar(
    card_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    row = await session.get(ClienteAppCardDia, card_id)
    if row is None:
        raise HTTPException(status_code=404, detail="card nao encontrado")
    await session.delete(row)
    await session.commit()
