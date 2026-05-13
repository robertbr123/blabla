"""GET/POST /api/v1/tecnico/me/* — endpoints do tecnico em campo."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.os import OsListItem, OsOut
from ondeline_api.api.schemas.tecnico_me import ConcluirIn, GpsUpdate, IniciarIn
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.business import Tecnico
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.repositories.ordem_servico import OrdemServicoRepo
from ondeline_api.repositories.tecnico import TecnicoRepo

router = APIRouter(prefix="/api/v1/tecnico/me", tags=["tecnico-me"])
_role_dep = Depends(require_role(Role.TECNICO))


async def current_tecnico(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Tecnico:
    repo = TecnicoRepo(session)
    tec = await repo.get_by_user_id(user.id)
    if tec is None:
        raise HTTPException(status_code=403, detail="user is not a tecnico")
    return tec


@router.get("/os", response_model=list[OsListItem], dependencies=[_role_dep])
async def my_os(
    session: Annotated[AsyncSession, Depends(get_db)],
    tec: Annotated[Tecnico, Depends(current_tecnico)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[OsListItem]:
    repo = OrdemServicoRepo(session)
    rows = await repo.list_for_tecnico(tec.id, status_filter=status_filter)
    return [OsListItem.model_validate(o) for o in rows]


@router.get("/os/{os_id}", response_model=OsOut, dependencies=[_role_dep])
async def my_os_detail(
    os_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    tec: Annotated[Tecnico, Depends(current_tecnico)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id_and_tecnico(os_id, tec.id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not assigned to you")
    return OsOut.model_validate(os_)


@router.post("/gps", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_role_dep])
async def update_gps(
    body: GpsUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    tec: Annotated[Tecnico, Depends(current_tecnico)],
) -> None:
    repo = TecnicoRepo(session)
    await repo.update_gps(tec, lat=body.lat, lng=body.lng)


@router.post(
    "/os/{os_id}/iniciar",
    response_model=OsOut,
    dependencies=[_role_dep],
)
async def iniciar_os(
    os_id: UUID,
    body: IniciarIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    tec: Annotated[Tecnico, Depends(current_tecnico)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id_and_tecnico(os_id, tec.id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not assigned to you")
    await repo.set_iniciada_with_gps(os_, lat=body.lat, lng=body.lng)
    return OsOut.model_validate(os_)


@router.post(
    "/os/{os_id}/concluir",
    response_model=OsOut,
    dependencies=[_role_dep],
)
async def concluir_os(
    os_id: UUID,
    body: ConcluirIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    tec: Annotated[Tecnico, Depends(current_tecnico)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id_and_tecnico(os_id, tec.id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not assigned to you")
    await repo.set_concluida_with_gps(
        os_, csat=body.csat, comentario=body.comentario, lat=body.lat, lng=body.lng
    )
    return OsOut.model_validate(os_)
