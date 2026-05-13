"""GET/POST/PATCH/DELETE /api/v1/manutencoes — admin only."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.deps_v1 import CursorParam, LimitParam, parse_cursor, parse_limit
from ondeline_api.api.schemas.manutencao import (
    ManutencaoCreate,
    ManutencaoOut,
    ManutencaoPatch,
)
from ondeline_api.api.schemas.pagination import CursorPage, encode_cursor
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.identity import Role
from ondeline_api.deps import get_db
from ondeline_api.repositories.manutencao import ManutencaoRepo

router = APIRouter(prefix="/api/v1/manutencoes", tags=["manutencoes"])
_admin_dep = Depends(require_role(Role.ADMIN))


@router.get("", response_model=CursorPage[ManutencaoOut], dependencies=[_admin_dep])
async def list_manutencoes(
    session: Annotated[AsyncSession, Depends(get_db)],
    cursor: CursorParam = None,
    limit: LimitParam = None,
    ativas: Annotated[bool | None, Query()] = None,
) -> CursorPage[ManutencaoOut]:
    repo = ManutencaoRepo(session)
    rows, next_cur = await repo.list_paginated(
        ativas=ativas, cursor=parse_cursor(cursor), limit=parse_limit(limit)
    )
    items = [ManutencaoOut.model_validate(m) for m in rows]
    return CursorPage[ManutencaoOut](
        items=items, next_cursor=encode_cursor(next_cur) if next_cur else None
    )


@router.post(
    "",
    response_model=ManutencaoOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin_dep],
)
async def create_manutencao(
    body: ManutencaoCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ManutencaoOut:
    repo = ManutencaoRepo(session)
    m = await repo.create(
        titulo=body.titulo,
        descricao=body.descricao,
        inicio_at=body.inicio_at,
        fim_at=body.fim_at,
        cidades=body.cidades,
        notificar=body.notificar,
    )
    return ManutencaoOut.model_validate(m)


@router.get("/{manutencao_id}", response_model=ManutencaoOut, dependencies=[_admin_dep])
async def get_manutencao(
    manutencao_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ManutencaoOut:
    repo = ManutencaoRepo(session)
    m = await repo.get_by_id(manutencao_id)
    if m is None:
        raise HTTPException(status_code=404, detail="manutencao not found")
    return ManutencaoOut.model_validate(m)


@router.patch("/{manutencao_id}", response_model=ManutencaoOut, dependencies=[_admin_dep])
async def patch_manutencao(
    manutencao_id: UUID,
    body: ManutencaoPatch,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ManutencaoOut:
    repo = ManutencaoRepo(session)
    m = await repo.get_by_id(manutencao_id)
    if m is None:
        raise HTTPException(status_code=404, detail="manutencao not found")
    await repo.update(
        m,
        titulo=body.titulo,
        descricao=body.descricao,
        inicio_at=body.inicio_at,
        fim_at=body.fim_at,
        cidades=body.cidades,
        notificar=body.notificar,
    )
    return ManutencaoOut.model_validate(m)


@router.delete(
    "/{manutencao_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_admin_dep],
)
async def delete_manutencao(
    manutencao_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = ManutencaoRepo(session)
    m = await repo.get_by_id(manutencao_id)
    if m is None:
        raise HTTPException(status_code=404, detail="manutencao not found")
    await repo.delete(m)
