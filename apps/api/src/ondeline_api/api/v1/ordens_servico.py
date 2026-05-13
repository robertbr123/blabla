"""GET/POST/PATCH /api/v1/os* — Ordens de Servico."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.deps_v1 import CursorParam, LimitParam, parse_cursor, parse_limit
from ondeline_api.api.schemas.os import (
    OsConcluirIn,
    OsCreate,
    OsListItem,
    OsOut,
    OsPatch,
)
from ondeline_api.api.schemas.pagination import CursorPage, encode_cursor
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.identity import Role
from ondeline_api.deps import get_db
from ondeline_api.domain.os_sequence import next_codigo
from ondeline_api.repositories.ordem_servico import OrdemServicoRepo

router = APIRouter(prefix="/api/v1/os", tags=["ordens-servico"])
_role_dep = Depends(require_role(Role.ATENDENTE, Role.ADMIN))

# Storage path for photos. In production this should be a configured volume.
FOTOS_DIR = Path("/tmp/ondeline_os_fotos")


@router.get("", response_model=CursorPage[OsListItem], dependencies=[_role_dep])
async def list_os(
    session: Annotated[AsyncSession, Depends(get_db)],
    cursor: CursorParam = None,
    limit: LimitParam = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    tecnico: Annotated[UUID | None, Query()] = None,
) -> CursorPage[OsListItem]:
    repo = OrdemServicoRepo(session)
    rows, next_cur = await repo.list_paginated(
        status=status_filter,
        tecnico_id=tecnico,
        cursor=parse_cursor(cursor),
        limit=parse_limit(limit),
    )
    items = [OsListItem.model_validate(o) for o in rows]
    return CursorPage[OsListItem](
        items=items,
        next_cursor=encode_cursor(next_cur) if next_cur else None,
    )


@router.post("", response_model=OsOut, status_code=status.HTTP_201_CREATED, dependencies=[_role_dep])
async def create_os(
    body: OsCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    codigo = await next_codigo(session)
    os_ = await repo.create(
        codigo=codigo,
        cliente_id=body.cliente_id,
        tecnico_id=None,
        problema=body.problema,
        endereco=body.endereco,
    )
    if body.agendamento_at:
        os_.agendamento_at = body.agendamento_at
        await session.flush()
    return OsOut.model_validate(os_)


@router.get("/{os_id}", response_model=OsOut, dependencies=[_role_dep])
async def get_os(
    os_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not found")
    return OsOut.model_validate(os_)


@router.patch("/{os_id}", response_model=OsOut, dependencies=[_role_dep])
async def patch_os(
    os_id: UUID,
    body: OsPatch,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not found")
    await repo.update(
        os_,
        status=body.status,
        tecnico_id=body.tecnico_id,
        agendamento_at=body.agendamento_at,
    )
    return OsOut.model_validate(os_)


@router.post(
    "/{os_id}/foto",
    response_model=OsOut,
    dependencies=[_role_dep],
)
async def upload_foto(
    os_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not found")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="file must be an image")
    target_dir = FOTOS_DIR / str(os_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{uuid4().hex}{Path(file.filename or 'foto.jpg').suffix or '.jpg'}"
    fpath = target_dir / fname
    contents = await file.read()
    fpath.write_bytes(contents)
    fpath.chmod(0o600)
    await repo.add_foto(
        os_,
        {
            "url": str(fpath),
            "ts": datetime.now(tz=UTC).isoformat(),
            "size": len(contents),
            "mime": file.content_type,
        },
    )
    return OsOut.model_validate(os_)


@router.post(
    "/{os_id}/concluir",
    response_model=OsOut,
    dependencies=[_role_dep],
)
async def concluir_os(
    os_id: UUID,
    body: OsConcluirIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not found")
    await repo.concluir(os_, csat=body.csat, comentario=body.comentario)
    return OsOut.model_validate(os_)
