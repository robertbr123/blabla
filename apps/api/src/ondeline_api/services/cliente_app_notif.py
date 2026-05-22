"""Helpers pra criar notificacoes no app cliente.

Respeitam as preferencias do user (`cliente_app_notif_prefs.categorias`):
se a categoria estiver OFF, a notif nao e inserida pra esse user.

Quando user tem `push_token`, dispara push FCM via celery task
(fire-and-forget). Falha no FCM nao trava criacao da notif no DB.

Broadcast aceita filtro por cidade — faz join `ClienteAppUser → Cliente`
via cpf_hash pra resolver a cidade SGP de cada user.
"""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Cliente
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


def _enqueue_push(
    user_id: UUID,
    push_token: str | None,
    categoria: str,
    titulo: str,
    corpo: str,
    payload: dict[str, object] | None,
) -> None:
    """Dispara push FCM via celery (fire-and-forget).

    Lazy import pra evitar import circular celery → service → celery.
    Stringifica payload pra `data` do FCM (so aceita string).
    """
    if not push_token:
        return
    try:
        from ondeline_api.workers.fcm_push import send_user_push

        data: dict[str, str] = {"categoria": categoria}
        if payload:
            for k, v in payload.items():
                data[k] = str(v)
        send_user_push.delay(
            str(user_id), push_token, titulo, corpo, data
        )
    except Exception as e:  # noqa: BLE001
        log.warning("notif.push_enqueue_failed", error=str(e))


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

    Se user tem push_token, enfileira push FCM out-of-app.
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

    # Push out-of-app — pega token diretamente do user pra evitar reload.
    user = await session.get(ClienteAppUser, user_id)
    if user is not None and user.push_token:
        _enqueue_push(user_id, user.push_token, categoria, titulo, corpo, payload)

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
    """Cria notif pra users ativos (status='active'), opcionalmente filtrando
    por cidade SGP.

    Filtro por cidade resolve `ClienteAppUser.cpf_hash → Cliente.cpf_hash`
    (cliente do cache SGP) e filtra `Cliente.cidade ILIKE %cidade%`.
    Users sem match em Cliente sao pulados quando cidade != None.

    Retorna quantidade criada.
    """
    if cidade:
        # Join via cpf_hash. Pega tupla (user, cliente).
        stmt = (
            select(ClienteAppUser, Cliente)
            .join(Cliente, Cliente.cpf_hash == ClienteAppUser.cpf_hash)
            .where(
                ClienteAppUser.status == "active",
                Cliente.cidade.ilike(f"%{cidade}%"),
            )
        )
        rows = list((await session.execute(stmt)).all())
        users = [u for u, _c in rows]
    else:
        stmt2 = select(ClienteAppUser).where(ClienteAppUser.status == "active")
        users = list((await session.execute(stmt2)).scalars())

    cnt = 0
    for u in users:
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
        if u.push_token:
            _enqueue_push(u.id, u.push_token, categoria, titulo, corpo, payload)
        cnt += 1
    if cnt > 0:
        await session.flush()
    log.info(
        "notif.broadcast",
        categoria=categoria,
        criadas=cnt,
        cidade=cidade,
    )
    return cnt


async def broadcast_cidades(
    session: AsyncSession,
    categoria: str,
    titulo: str,
    corpo: str = "",
    action: str | None = None,
    payload: dict[str, object] | None = None,
    cidades: list[str] | None = None,
) -> int:
    """Helper de manutencao: itera lista de cidades e somatoriza.

    Se `cidades` for None/vazia, faz broadcast geral.
    """
    if not cidades:
        return await broadcast(session, categoria, titulo, corpo, action, payload)
    total = 0
    seen_users: set[UUID] = set()
    for cid in cidades:
        # Pra evitar duplicacao de notif quando user mora em cidade que
        # casa com varios filtros, fazemos broadcast por cidade e
        # consultamos quem ja recebeu nessa iteracao (best-effort —
        # commit do caller deduplica via DB se quiser).
        stmt = (
            select(ClienteAppUser, Cliente)
            .join(Cliente, Cliente.cpf_hash == ClienteAppUser.cpf_hash)
            .where(
                ClienteAppUser.status == "active",
                Cliente.cidade.ilike(f"%{cid}%"),
            )
        )
        rows = list((await session.execute(stmt)).all())
        for u, _c in rows:
            if u.id in seen_users:
                continue
            seen_users.add(u.id)
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
            if u.push_token:
                _enqueue_push(
                    u.id, u.push_token, categoria, titulo, corpo, payload
                )
            total += 1
    if total > 0:
        await session.flush()
    log.info(
        "notif.broadcast_cidades",
        categoria=categoria,
        criadas=total,
        cidades=cidades,
    )
    return total
