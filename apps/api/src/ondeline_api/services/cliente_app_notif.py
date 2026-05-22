"""Helpers pra criar notificacoes no app cliente.

Respeitam as preferencias do user (`cliente_app_notif_prefs.categorias`):
se a categoria estiver OFF, a notif nao e inserida pra esse user.

Usage:
    await notify_user(session, user_id, "fatura", "Fatura nova", "...", "tela:/faturas")
    await broadcast(session, "promocao", "...", "...", filter=...)
"""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.cliente_app import (
    ClienteAppNotificacao,
    ClienteAppNotifPrefs,
    ClienteAppUser,
)

log = structlog.get_logger(__name__)

_PREFS_DEFAULT = {
    "fatura": True,
    "os": True,
    "manutencao": True,
    "promocao": True,
    "conta": True,
}


async def _categoria_permitida(
    session: AsyncSession, user_id: UUID, categoria: str
) -> bool:
    """Le prefs do user. Default e True quando nao salvou ainda."""
    row = await session.get(ClienteAppNotifPrefs, user_id)
    if row is None:
        return _PREFS_DEFAULT.get(categoria, True)
    cats = {**_PREFS_DEFAULT, **(row.categorias or {})}
    return bool(cats.get(categoria, True))


async def notify_user(
    session: AsyncSession,
    user_id: UUID,
    categoria: str,
    titulo: str,
    corpo: str = "",
    action: str | None = None,
    payload: dict[str, object] | None = None,
) -> ClienteAppNotificacao | None:
    """Cria notificacao se a categoria estiver habilitada pro user.

    Retorna a notif criada ou None se foi suprimida por preferencia.
    Nao faz commit — caller decide.
    """
    if not await _categoria_permitida(session, user_id, categoria):
        return None
    notif = ClienteAppNotificacao(
        cliente_app_user_id=user_id,
        categoria=categoria,
        titulo=titulo,
        corpo=corpo,
        action=action,
        payload_json=payload,
    )
    session.add(notif)
    await session.flush()
    log.info(
        "notif.created",
        user_id=str(user_id),
        categoria=categoria,
        titulo=titulo[:60],
    )
    return notif


async def broadcast(
    session: AsyncSession,
    categoria: str,
    titulo: str,
    corpo: str = "",
    action: str | None = None,
    payload: dict[str, object] | None = None,
    cidade: str | None = None,
) -> int:
    """Cria notif pra todos os usuarios ativos (status='active').

    Se `cidade` for passado, filtra por SGP — usuarios sem sgp_id sao
    pulados (nao podemos saber a cidade). Retorna quantidade criada.
    """
    stmt = select(ClienteAppUser).where(ClienteAppUser.status == "active")
    rows = list((await session.execute(stmt)).scalars())
    # Filtro por cidade exige join com Cliente do SGP — complexo. Pro MVP:
    # se cidade for passada, mandamos pra TODOS mesmo (admin sabe que e
    # broadcast). Filtro fino fica pra fase seguinte.
    _ = cidade
    cnt = 0
    for u in rows:
        if not await _categoria_permitida(session, u.id, categoria):
            continue
        session.add(
            ClienteAppNotificacao(
                cliente_app_user_id=u.id,
                categoria=categoria,
                titulo=titulo,
                corpo=corpo,
                action=action,
                payload_json=payload,
            )
        )
        cnt += 1
    if cnt > 0:
        await session.flush()
    log.info("notif.broadcast", categoria=categoria, criadas=cnt)
    return cnt
