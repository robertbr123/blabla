"""Card do dia — rotaciona conteudo na Home do app cliente.

Backend escolhe 1 card ativo por dia/usuario via hash deterministico:
mesmo (user_id, data) sempre devolve o mesmo card. Quando o dia vira,
proximo card da lista. Pra cliente novo, sempre comeca de um indice
diferente (hash inclui user_id).
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.db.models.cliente_app import (
    ClienteAppCardDia,
    ClienteAppUser,
)
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
