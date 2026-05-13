"""GET/POST/PATCH/DELETE /api/v1/tecnicos — gerenciamento de tecnicos."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.pagination import CursorPage
from ondeline_api.api.schemas.tecnico import (
    AreaCreate,
    AreaOut,
    TecnicoCreate,
    TecnicoListItem,
    TecnicoOut,
    TecnicoPatch,
)
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.identity import Role
from ondeline_api.deps import get_db
from ondeline_api.repositories.tecnico import TecnicoRepo

router = APIRouter(prefix="/api/v1/tecnicos", tags=["tecnicos"])
_admin_dep = Depends(require_role(Role.ADMIN))


@router.get("", response_model=CursorPage[TecnicoListItem], dependencies=[_admin_dep])
async def list_tecnicos(
    session: Annotated[AsyncSession, Depends(get_db)],
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
    ativo: Annotated[bool | None, Query()] = None,
) -> CursorPage[TecnicoListItem]:
    repo = TecnicoRepo(session)
    cursor_uuid: UUID | None = None
    if cursor:
        try:
            cursor_uuid = UUID(cursor)
        except ValueError:
            cursor_uuid = None
    rows, next_cur = await repo.list_paginated(
        ativo=ativo, cursor=cursor_uuid, limit=limit or 50
    )
    items = [TecnicoListItem.model_validate(t) for t in rows]
    return CursorPage[TecnicoListItem](
        items=items, next_cursor=str(next_cur) if next_cur else None
    )


@router.post(
    "",
    response_model=TecnicoOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin_dep],
)
async def create_tecnico(
    body: TecnicoCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TecnicoOut:
    repo = TecnicoRepo(session)
    tec = await repo.create(
        nome=body.nome, whatsapp=body.whatsapp, ativo=body.ativo, user_id=body.user_id
    )
    return TecnicoOut.model_validate(tec)


@router.get("/{tecnico_id}", response_model=TecnicoOut, dependencies=[_admin_dep])
async def get_tecnico(
    tecnico_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TecnicoOut:
    repo = TecnicoRepo(session)
    tec = await repo.get_by_id(tecnico_id)
    if tec is None:
        raise HTTPException(status_code=404, detail="tecnico not found")
    areas = await repo.list_areas(tec.id)
    out = TecnicoOut.model_validate(tec)
    out.areas = [AreaOut.model_validate(a) for a in areas]
    return out


@router.patch("/{tecnico_id}", response_model=TecnicoOut, dependencies=[_admin_dep])
async def patch_tecnico(
    tecnico_id: UUID,
    body: TecnicoPatch,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TecnicoOut:
    repo = TecnicoRepo(session)
    tec = await repo.get_by_id(tecnico_id)
    if tec is None:
        raise HTTPException(status_code=404, detail="tecnico not found")
    await repo.update(
        tec,
        nome=body.nome,
        whatsapp=body.whatsapp,
        ativo=body.ativo,
        gps_lat=body.gps_lat,
        gps_lng=body.gps_lng,
    )
    return TecnicoOut.model_validate(tec)


@router.delete(
    "/{tecnico_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_admin_dep],
)
async def delete_tecnico(
    tecnico_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = TecnicoRepo(session)
    tec = await repo.get_by_id(tecnico_id)
    if tec is None:
        raise HTTPException(status_code=404, detail="tecnico not found")
    await repo.delete(tec)


@router.get(
    "/{tecnico_id}/areas",
    response_model=list[AreaOut],
    dependencies=[_admin_dep],
)
async def list_areas(
    tecnico_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[AreaOut]:
    repo = TecnicoRepo(session)
    areas = await repo.list_areas(tecnico_id)
    return [AreaOut.model_validate(a) for a in areas]


@router.post(
    "/{tecnico_id}/areas",
    response_model=AreaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin_dep],
)
async def add_area(
    tecnico_id: UUID,
    body: AreaCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AreaOut:
    repo = TecnicoRepo(session)
    tec = await repo.get_by_id(tecnico_id)
    if tec is None:
        raise HTTPException(status_code=404, detail="tecnico not found")
    area = await repo.add_area(
        tecnico_id, cidade=body.cidade, rua=body.rua, prioridade=body.prioridade
    )
    return AreaOut.model_validate(area)


@router.delete(
    "/{tecnico_id}/areas/{cidade}/{rua}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_admin_dep],
)
async def remove_area(
    tecnico_id: UUID,
    cidade: str,
    rua: str,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = TecnicoRepo(session)
    ok = await repo.remove_area(tecnico_id, cidade, rua)
    if not ok:
        raise HTTPException(status_code=404, detail="area not found")
