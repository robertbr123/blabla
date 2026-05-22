"""Router admin pra chat do app cliente.

- Atendente lista mensagens, envia (role=atendente), assume e libera o handoff.
- Quando handoff ativo, bot nao responde automaticamente (ver
  `cliente_app_chat.send`).
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.rbac import require_role
from ondeline_api.db.crypto import decrypt_pii, encrypt_pii
from ondeline_api.db.models.cliente_app import ClienteAppMessage, ClienteAppUser
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db

admin_router = APIRouter(
    prefix="/api/v1/admin/cliente-app-chat",
    tags=["admin:cliente-app-chat"],
)


class AdminChatMessage(BaseModel):
    id: str
    role: str  # user | bot | atendente
    content: str
    atendente_user_id: str | None = None
    created_at: str


class AdminChatThreadOut(BaseModel):
    user_id: str
    user_nome: str
    handoff_active: bool
    handoff_atendente_id: str | None
    handoff_atendente_nome: str | None
    handoff_at: str | None
    messages: list[AdminChatMessage]


class AdminChatSendIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


@admin_router.get(
    "/{user_id}",
    response_model=AdminChatThreadOut,
    dependencies=[Depends(require_role(Role.ATENDENTE, Role.ADMIN))],
)
async def get_thread(
    user_id: UUID,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> AdminChatThreadOut:
    u = await session.get(ClienteAppUser, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado")

    stmt = (
        select(ClienteAppMessage)
        .where(ClienteAppMessage.cliente_app_user_id == user_id)
        .order_by(asc(ClienteAppMessage.created_at))
    )
    rows = list((await session.execute(stmt)).scalars())

    handoff_atendente: User | None = None
    if u.human_handoff_atendente_id:
        handoff_atendente = await session.get(User, u.human_handoff_atendente_id)

    return AdminChatThreadOut(
        user_id=str(u.id),
        user_nome=decrypt_pii(u.nome_encrypted) if u.nome_encrypted else "",
        handoff_active=u.human_handoff_atendente_id is not None,
        handoff_atendente_id=str(u.human_handoff_atendente_id)
        if u.human_handoff_atendente_id
        else None,
        handoff_atendente_nome=handoff_atendente.name if handoff_atendente else None,
        handoff_at=u.human_handoff_at.isoformat() if u.human_handoff_at else None,
        messages=[
            AdminChatMessage(
                id=str(m.id),
                role=m.role,
                content=decrypt_pii(m.content_encrypted),
                atendente_user_id=None,  # nao gravamos por enquanto, role=atendente ja basta
                created_at=m.created_at.isoformat(),
            )
            for m in rows
        ],
    )


@admin_router.post(
    "/{user_id}/take",
    response_model=AdminChatThreadOut,
)
async def take(
    user_id: UUID,
    current_user: User = Depends(require_role(Role.ATENDENTE, Role.ADMIN)),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> AdminChatThreadOut:
    u = await session.get(ClienteAppUser, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado")
    u.human_handoff_atendente_id = current_user.id
    u.human_handoff_at = datetime.now(UTC)
    await session.flush()
    await session.commit()
    return await get_thread(user_id, session)


@admin_router.post(
    "/{user_id}/release",
    response_model=AdminChatThreadOut,
    dependencies=[Depends(require_role(Role.ATENDENTE, Role.ADMIN))],
)
async def release(
    user_id: UUID,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> AdminChatThreadOut:
    u = await session.get(ClienteAppUser, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado")
    u.human_handoff_atendente_id = None
    u.human_handoff_at = None
    await session.flush()
    await session.commit()
    return await get_thread(user_id, session)


@admin_router.post(
    "/{user_id}/send",
    response_model=AdminChatMessage,
)
async def send(
    user_id: UUID,
    body: AdminChatSendIn,
    current_user: User = Depends(require_role(Role.ATENDENTE, Role.ADMIN)),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> AdminChatMessage:
    u = await session.get(ClienteAppUser, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado")

    # Garante handoff ativo (auto-take se nao estiver)
    if u.human_handoff_atendente_id is None:
        u.human_handoff_atendente_id = current_user.id
        u.human_handoff_at = datetime.now(UTC)

    msg = ClienteAppMessage(
        cliente_app_user_id=user_id,
        role="atendente",
        content_encrypted=encrypt_pii(body.text),
    )
    session.add(msg)
    await session.flush()
    await session.commit()
    await session.refresh(msg)

    return AdminChatMessage(
        id=str(msg.id),
        role="atendente",
        content=body.text,
        atendente_user_id=str(current_user.id),
        created_at=msg.created_at.isoformat(),
    )
