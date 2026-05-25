"""GET/POST/PATCH /api/v1/canais — CRUD admin de canais WhatsApp (F4)."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.canal import CanalCreate, CanalOut, CanalUpdate
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.business import Canal
from ondeline_api.db.models.identity import Role
from ondeline_api.deps import get_db
from ondeline_api.repositories.canal import CanalRepo

router = APIRouter(prefix="/api/v1/canais", tags=["canais"])
_admin_dep = Depends(require_role(Role.ADMIN))
_admin_or_atendente_dep = Depends(require_role(Role.ADMIN, Role.ATENDENTE))


@router.get("", response_model=list[CanalOut], dependencies=[_admin_or_atendente_dep])
async def list_canais(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[CanalOut]:
    repo = CanalRepo(session)
    rows = await repo.list_all()
    return [CanalOut.model_validate(c) for c in rows]


@router.post(
    "",
    response_model=CanalOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin_dep],
)
async def create_canal(
    body: CanalCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CanalOut:
    canal = Canal(
        slug=body.slug,
        nome=body.nome,
        provider=body.provider,
        evolution_instance=body.evolution_instance,
        cloud_phone_id=body.cloud_phone_id,
        cloud_waba_id=body.cloud_waba_id,
        prompt_variant=body.prompt_variant,
        ativo=body.ativo,
        horario_inicio=body.horario_inicio,
        horario_fim=body.horario_fim,
        msg_fora_horario=body.msg_fora_horario,
    )
    session.add(canal)
    try:
        await session.flush()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="slug, evolution_instance ou cloud_phone_id ja em uso",
        ) from e
    return CanalOut.model_validate(canal)


@router.patch(
    "/{canal_id}",
    response_model=CanalOut,
    dependencies=[_admin_dep],
)
async def update_canal(
    canal_id: UUID,
    body: CanalUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CanalOut:
    repo = CanalRepo(session)
    canal = await repo.get_by_id(canal_id)
    if canal is None:
        raise HTTPException(status_code=404, detail="canal not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(canal, field, value)
    try:
        await session.flush()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="evolution_instance ou cloud_phone_id ja em uso por outro canal",
        ) from e
    return CanalOut.model_validate(canal)
