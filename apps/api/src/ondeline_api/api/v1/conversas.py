"""GET/POST /api/v1/conversas* — atendimento de conversas."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.deps_v1 import CursorParam, LimitParam, parse_cursor, parse_limit
from ondeline_api.api.schemas.conversa import (
    ClienteEmbutido,
    ConversaListItem,
    ConversaOut,
    ResponderIn,
)
from ondeline_api.api.schemas.mensagem import MensagemOut
from ondeline_api.api.schemas.pagination import CursorPage, encode_cursor
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import Cliente, Mensagem
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.repositories.conversa import ConversaRepo
from ondeline_api.services.conversa_attend import (
    ConversaNotFound,
    atender,
    encerrar,
)
from ondeline_api.services.responder import responder
from ondeline_api.workers.runtime import CeleryOutboundEnqueuer, get_redis

router = APIRouter(prefix="/api/v1/conversas", tags=["conversas"])
_role_dep = Depends(require_role(Role.ATENDENTE, Role.ADMIN))


def _to_msg_out(m: Mensagem) -> MensagemOut:
    return MensagemOut(
        id=m.id,
        conversa_id=m.conversa_id,
        role=m.role.value,
        content=decrypt_pii(m.content_encrypted) if m.content_encrypted else None,
        media_type=m.media_type,
        media_url=m.media_url,
        created_at=m.created_at,
    )


@router.get("", response_model=CursorPage[ConversaListItem], dependencies=[_role_dep])
async def list_conversas(
    session: Annotated[AsyncSession, Depends(get_db)],
    cursor: CursorParam = None,
    limit: LimitParam = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query()] = None,
) -> CursorPage[ConversaListItem]:
    repo = ConversaRepo(session)
    rows, next_cur = await repo.list_paginated(
        status=status_filter,
        q=q,
        cursor=parse_cursor(cursor),
        limit=parse_limit(limit),
    )
    items = [ConversaListItem.model_validate(c) for c in rows]
    return CursorPage[ConversaListItem](
        items=items, next_cursor=encode_cursor(next_cur) if next_cur else None
    )


@router.get("/{conversa_id}", response_model=ConversaOut, dependencies=[_role_dep])
async def get_conversa(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ConversaOut:
    from sqlalchemy import select

    repo = ConversaRepo(session)
    c = await repo.get_by_id(conversa_id)
    if c is None:
        raise HTTPException(status_code=404, detail="conversa not found")
    msgs, _ = await repo.list_messages(c.id, limit=50)
    out = ConversaOut.model_validate(c)
    out.mensagens = [_to_msg_out(m) for m in msgs]

    if c.cliente_id is not None:
        cliente_row = (
            await session.execute(select(Cliente).where(Cliente.id == c.cliente_id))
        ).scalar_one_or_none()
        if cliente_row is not None:
            out.cliente = ClienteEmbutido(
                id=cliente_row.id,
                nome=decrypt_pii(cliente_row.nome_encrypted) if cliente_row.nome_encrypted else "",
                cpf_cnpj=decrypt_pii(cliente_row.cpf_cnpj_encrypted) if cliente_row.cpf_cnpj_encrypted else "",
                whatsapp=cliente_row.whatsapp,
                plano=cliente_row.plano,
                cidade=cliente_row.cidade,
                endereco=decrypt_pii(cliente_row.endereco_encrypted) if cliente_row.endereco_encrypted else None,
            )
    return out


@router.get(
    "/{conversa_id}/mensagens",
    response_model=CursorPage[MensagemOut],
    dependencies=[_role_dep],
)
async def list_messages(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    cursor: CursorParam = None,
    limit: LimitParam = None,
) -> CursorPage[MensagemOut]:
    repo = ConversaRepo(session)
    msgs, next_cur = await repo.list_messages(
        conversa_id, cursor=parse_cursor(cursor), limit=parse_limit(limit)
    )
    items = [_to_msg_out(m) for m in msgs]
    return CursorPage[MensagemOut](
        items=items, next_cursor=encode_cursor(next_cur) if next_cur else None
    )


@router.post(
    "/{conversa_id}/atender",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_role_dep],
)
async def atender_endpoint(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    try:
        await atender(session, conversa_id, user.id)
    except ConversaNotFound as exc:
        raise HTTPException(status_code=404, detail="conversa not found") from exc


@router.post(
    "/{conversa_id}/responder",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_role_dep],
)
async def responder_endpoint(
    conversa_id: UUID,
    body: ResponderIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    enqueuer = CeleryOutboundEnqueuer()
    redis = await get_redis()
    try:
        await responder(session, conversa_id, user.id, body.text, enqueuer, redis=redis)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="conversa not found") from exc


@router.post(
    "/{conversa_id}/encerrar",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_role_dep],
)
async def encerrar_endpoint(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    try:
        await encerrar(session, conversa_id)
    except ConversaNotFound as exc:
        raise HTTPException(status_code=404, detail="conversa not found") from exc


@router.delete(
    "/{conversa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_role_dep],
)
async def delete_conversa(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = ConversaRepo(session)
    c = await repo.get_by_id(conversa_id)
    if c is None:
        raise HTTPException(status_code=404, detail="conversa not found")
    await repo.soft_delete(c)
