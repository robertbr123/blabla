"""Central de notificacoes do app cliente (B5).

- GET /api/v1/cliente-app/notificacoes — lista paginada (mais recentes primeiro).
- GET /api/v1/cliente-app/notificacoes/unread-count — contador pro badge.
- POST /api/v1/cliente-app/notificacoes/{id}/lida — marca como lida.
- POST /api/v1/cliente-app/notificacoes/marcar-todas-lidas — bulk.
- GET/PUT /api/v1/cliente-app/notificacoes/preferencias — prefs por categoria.

Push real-time (Firebase Messaging) e progressive enhancement futuro —
hoje as notificacoes sao geradas server-side em eventos (fatura criada,
OS atualizada, manutencao programada, promo nova) e o cliente ve no
sino quando abre o app.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.db.models.cliente_app import (
    ClienteAppNotificacao,
    ClienteAppNotifPrefs,
    ClienteAppUser,
)
from ondeline_api.deps import get_db

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/cliente-app/notificacoes",
    tags=["cliente-app:notificacoes"],
)

# Categorias suportadas no app.
CATEGORIAS = {"fatura", "os", "manutencao", "promocao", "conta", "outro"}
PREFS_DEFAULT = {
    "fatura": True,
    "os": True,
    "manutencao": True,
    "promocao": True,
    "conta": True,
}


class NotificacaoOut(BaseModel):
    id: UUID
    categoria: str
    titulo: str
    corpo: str
    action: str | None
    lida: bool
    created_at: datetime


class UnreadCountOut(BaseModel):
    count: int


class PrefsOut(BaseModel):
    categorias: dict[str, bool]


class PrefsIn(BaseModel):
    categorias: dict[str, bool] = Field(
        default_factory=lambda: dict(PREFS_DEFAULT)
    )


def _notif_out(n: ClienteAppNotificacao) -> NotificacaoOut:
    return NotificacaoOut(
        id=n.id,
        categoria=n.categoria,
        titulo=n.titulo,
        corpo=n.corpo,
        action=n.action,
        lida=n.lida_em is not None,
        created_at=n.created_at,
    )


@router.get("", response_model=list[NotificacaoOut])
async def listar(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[NotificacaoOut]:
    stmt = (
        select(ClienteAppNotificacao)
        .where(ClienteAppNotificacao.cliente_app_user_id == user.id)
        .order_by(desc(ClienteAppNotificacao.created_at))
        .limit(limit)
    )
    rows = list((await session.execute(stmt)).scalars())
    return [_notif_out(n) for n in rows]


@router.get("/unread-count", response_model=UnreadCountOut)
async def unread_count(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> UnreadCountOut:
    cnt = (
        await session.execute(
            select(func.count(ClienteAppNotificacao.id)).where(
                ClienteAppNotificacao.cliente_app_user_id == user.id,
                ClienteAppNotificacao.lida_em.is_(None),
            )
        )
    ).scalar_one()
    return UnreadCountOut(count=int(cnt or 0))


@router.post("/{notif_id}/lida", response_model=NotificacaoOut)
async def marcar_lida(
    notif_id: UUID,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> NotificacaoOut:
    n = await session.get(ClienteAppNotificacao, notif_id)
    if n is None or n.cliente_app_user_id != user.id:
        raise HTTPException(status_code=404, detail="Notificacao nao encontrada")
    if n.lida_em is None:
        n.lida_em = datetime.now(tz=UTC)
        await session.commit()
        await session.refresh(n)
    return _notif_out(n)


@router.post("/marcar-todas-lidas", response_model=UnreadCountOut)
async def marcar_todas(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> UnreadCountOut:
    await session.execute(
        update(ClienteAppNotificacao)
        .where(
            ClienteAppNotificacao.cliente_app_user_id == user.id,
            ClienteAppNotificacao.lida_em.is_(None),
        )
        .values(lida_em=datetime.now(tz=UTC))
    )
    await session.commit()
    return UnreadCountOut(count=0)


@router.get("/preferencias", response_model=PrefsOut)
async def get_prefs(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PrefsOut:
    row = await session.get(ClienteAppNotifPrefs, user.id)
    if row is None:
        return PrefsOut(categorias=dict(PREFS_DEFAULT))
    return PrefsOut(categorias={**PREFS_DEFAULT, **row.categorias})


@router.put("/preferencias", response_model=PrefsOut)
async def set_prefs(
    body: PrefsIn,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PrefsOut:
    # Filtra so categorias conhecidas.
    cleaned = {k: bool(v) for k, v in body.categorias.items() if k in CATEGORIAS}
    merged = {**PREFS_DEFAULT, **cleaned}
    row = await session.get(ClienteAppNotifPrefs, user.id)
    if row is None:
        row = ClienteAppNotifPrefs(
            cliente_app_user_id=user.id,
            categorias=merged,
        )
        session.add(row)
    else:
        row.categorias = merged
        row.updated_at = datetime.now(tz=UTC)
    await session.commit()
    return PrefsOut(categorias=merged)
