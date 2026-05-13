"""SSE endpoint for live conversation events.

GET /api/v1/conversas/{id}/stream — long-lived connection, emits events
as JSON lines. Client uses native EventSource.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.repositories.conversa import ConversaRepo
from ondeline_api.services.conversa_events import subscribe
from ondeline_api.workers.runtime import get_redis

router = APIRouter(prefix="/api/v1/conversas", tags=["conversas-stream"])


@router.get(
    "/{conversa_id}/stream",
    dependencies=[Depends(require_role(Role.ATENDENTE, Role.ADMIN))],
)
async def stream_conversa(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> EventSourceResponse:
    repo = ConversaRepo(session)
    c = await repo.get_by_id(conversa_id)
    if c is None:
        raise HTTPException(status_code=404, detail="conversa not found")

    async def _gen() -> AsyncIterator[dict[str, str]]:
        redis = await get_redis()
        async for event in subscribe(redis, conversa_id):
            yield {"event": event.get("type", "msg"), "data": json.dumps(event)}

    return EventSourceResponse(_gen())
