"""SSE endpoint for live conversation events.

EventSource nao envia Authorization header. Fluxo: o front faz POST
/stream-ticket (autenticado normal) e abre o GET /stream?ticket=<jwt 60s>.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.engine import get_sessionmaker
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.repositories.conversa import ConversaRepo
from ondeline_api.services.conversa_events import subscribe
from ondeline_api.workers.runtime import get_redis

router = APIRouter(prefix="/api/v1/conversas", tags=["conversas-stream"])

_ROLES_STREAM = (Role.ATENDENTE.value, Role.ADMIN.value)


@router.post(
    "/{conversa_id}/stream-ticket",
    dependencies=[Depends(require_role(Role.ATENDENTE, Role.ADMIN))],
)
async def stream_ticket(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    repo = ConversaRepo(session)
    c = await repo.get_by_id(conversa_id)
    if c is None:
        raise HTTPException(status_code=404, detail="conversa not found")
    return {"ticket": jwt_mod.encode_sse_ticket(user.id, user.role.value, conversa_id)}


@router.get("/{conversa_id}/stream")
async def stream_conversa(
    conversa_id: UUID,
    ticket: Annotated[str, Query()],
) -> EventSourceResponse:
    try:
        payload = jwt_mod.decode_sse_ticket(ticket)
    except jwt_mod.TokenExpired:
        raise HTTPException(status_code=401, detail="ticket expired") from None
    except jwt_mod.InvalidToken as exc:
        raise HTTPException(status_code=401, detail="invalid ticket") from exc
    if payload.get("conversa_id") != str(conversa_id):
        raise HTTPException(status_code=403, detail="ticket nao corresponde a conversa")
    # Role/ativo sao snapshot do momento da emissao do ticket (60s). Um user
    # desativado nesse intervalo ainda abre o stream - aceito: stream e
    # read-only de UMA conversa que ele ja podia ler, e access tokens do
    # sistema tambem so expiram em ate 15min sem denylist.
    if payload.get("role") not in _ROLES_STREAM:
        raise HTTPException(status_code=403, detail="role nao autorizado")

    # Sessao curta SO pro 404 check. NAO usar Depends(get_db) aqui: a
    # dependency so fecha quando a resposta termina, e num SSE long-lived
    # isso seguraria uma conexao do pool pela vida inteira do stream.
    sm = get_sessionmaker()
    async with sm() as session:
        c = await ConversaRepo(session).get_by_id(conversa_id)
    if c is None:
        raise HTTPException(status_code=404, detail="conversa not found")

    async def _gen() -> AsyncIterator[dict[str, str]]:
        redis = await get_redis()
        async for event in subscribe(redis, conversa_id):
            yield {"event": event.get("type", "msg"), "data": json.dumps(event)}

    return EventSourceResponse(_gen())
