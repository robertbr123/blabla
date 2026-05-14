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
    TecnicoUserCreate,
    TecnicoUserOut,
    TecnicoUserPatch,
    TecnicoUserResetPassword,
)
from ondeline_api.auth.audit import write_audit
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.business import Tecnico
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.repositories.tecnico import TecnicoRepo
from ondeline_api.services.tecnico_user import (
    TecnicoUserError,
    create_user_for_tecnico,
    reset_user_password,
    set_user_active,
)

router = APIRouter(prefix="/api/v1/tecnicos", tags=["tecnicos"])
_admin_dep = Depends(require_role(Role.ADMIN))


async def _build_out(session: AsyncSession, tec: Tecnico) -> TecnicoOut:
    out = TecnicoOut.model_validate(tec)
    areas = await TecnicoRepo(session).list_areas(tec.id)
    out.areas = [AreaOut.model_validate(a) for a in areas]
    if tec.user_id is not None:
        user = await session.get(User, tec.user_id)
        if user is not None:
            out.user = TecnicoUserOut.model_validate(user)
    return out


async def _get_tecnico_or_404(session: AsyncSession, tecnico_id: UUID) -> Tecnico:
    tec = await TecnicoRepo(session).get_by_id(tecnico_id)
    if tec is None:
        raise HTTPException(status_code=404, detail="tecnico not found")
    return tec


async def _get_linked_user_or_404(session: AsyncSession, tec: Tecnico) -> User:
    if tec.user_id is None:
        raise HTTPException(status_code=404, detail="tecnico sem usuário de login")
    user = await session.get(User, tec.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="usuário vinculado não encontrado")
    return user


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
    actor: Annotated[User, Depends(get_current_user)],
) -> TecnicoOut:
    if (body.email is None) != (body.password is None):
        raise HTTPException(
            status_code=400, detail="email e password devem vir juntos (ou ambos vazios)"
        )
    if body.email is not None and body.user_id is not None:
        raise HTTPException(
            status_code=400, detail="forneça email+password OU user_id, não os dois"
        )

    repo = TecnicoRepo(session)
    tec = await repo.create(
        nome=body.nome, whatsapp=body.whatsapp, ativo=body.ativo, user_id=body.user_id
    )

    if body.email is not None and body.password is not None:
        try:
            user = await create_user_for_tecnico(
                session, tec, email=body.email, password=body.password, name=body.nome
            )
        except TecnicoUserError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        await write_audit(
            session,
            user_id=actor.id,
            action="user.create",
            resource_type="user",
            resource_id=str(user.id),
            after={"role": user.role.value, "tecnico_id": str(tec.id)},
        )
    return await _build_out(session, tec)


@router.get("/{tecnico_id}", response_model=TecnicoOut, dependencies=[_admin_dep])
async def get_tecnico(
    tecnico_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TecnicoOut:
    tec = await _get_tecnico_or_404(session, tecnico_id)
    return await _build_out(session, tec)


@router.patch("/{tecnico_id}", response_model=TecnicoOut, dependencies=[_admin_dep])
async def patch_tecnico(
    tecnico_id: UUID,
    body: TecnicoPatch,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TecnicoOut:
    tec = await _get_tecnico_or_404(session, tecnico_id)
    await TecnicoRepo(session).update(
        tec,
        nome=body.nome,
        whatsapp=body.whatsapp,
        ativo=body.ativo,
        gps_lat=body.gps_lat,
        gps_lng=body.gps_lng,
    )
    return await _build_out(session, tec)


@router.delete(
    "/{tecnico_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_admin_dep],
)
async def delete_tecnico(
    tecnico_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    tec = await _get_tecnico_or_404(session, tecnico_id)
    await TecnicoRepo(session).delete(tec)


@router.post(
    "/{tecnico_id}/user",
    response_model=TecnicoUserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin_dep],
)
async def create_tecnico_user(
    tecnico_id: UUID,
    body: TecnicoUserCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    actor: Annotated[User, Depends(get_current_user)],
) -> TecnicoUserOut:
    tec = await _get_tecnico_or_404(session, tecnico_id)
    try:
        user = await create_user_for_tecnico(
            session, tec, email=body.email, password=body.password, name=tec.nome
        )
    except TecnicoUserError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await write_audit(
        session,
        user_id=actor.id,
        action="user.create",
        resource_type="user",
        resource_id=str(user.id),
        after={"role": user.role.value, "tecnico_id": str(tec.id)},
    )
    return TecnicoUserOut.model_validate(user)


@router.post(
    "/{tecnico_id}/user/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_admin_dep],
)
async def reset_tecnico_user_password(
    tecnico_id: UUID,
    body: TecnicoUserResetPassword,
    session: Annotated[AsyncSession, Depends(get_db)],
    actor: Annotated[User, Depends(get_current_user)],
) -> None:
    tec = await _get_tecnico_or_404(session, tecnico_id)
    user = await _get_linked_user_or_404(session, tec)
    try:
        await reset_user_password(session, user, new_password=body.password)
    except TecnicoUserError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await write_audit(
        session,
        user_id=actor.id,
        action="user.password_reset",
        resource_type="user",
        resource_id=str(user.id),
    )


@router.patch(
    "/{tecnico_id}/user",
    response_model=TecnicoUserOut,
    dependencies=[_admin_dep],
)
async def patch_tecnico_user(
    tecnico_id: UUID,
    body: TecnicoUserPatch,
    session: Annotated[AsyncSession, Depends(get_db)],
    actor: Annotated[User, Depends(get_current_user)],
) -> TecnicoUserOut:
    tec = await _get_tecnico_or_404(session, tecnico_id)
    user = await _get_linked_user_or_404(session, tec)
    if body.is_active is not None and body.is_active != user.is_active:
        before = user.is_active
        await set_user_active(session, user, active=body.is_active)
        await write_audit(
            session,
            user_id=actor.id,
            action="user.set_active",
            resource_type="user",
            resource_id=str(user.id),
            before={"is_active": before},
            after={"is_active": user.is_active},
        )
    return TecnicoUserOut.model_validate(user)


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
    tec = await _get_tecnico_or_404(session, tecnico_id)
    area = await TecnicoRepo(session).add_area(
        tec.id, cidade=body.cidade, rua=body.rua, prioridade=body.prioridade
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
