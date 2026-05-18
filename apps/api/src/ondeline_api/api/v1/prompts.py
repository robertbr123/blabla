"""GET/POST/PATCH /api/v1/prompts — admin de variantes de prompt (F5 A/B test)."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.prompt_variant import (
    PromptVariantCreate,
    PromptVariantOut,
    PromptVariantStats,
    PromptVariantUpdate,
)
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.business import PromptVariant
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.repositories.prompt_variant import PromptVariantRepo

router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])
_admin_dep = Depends(require_role(Role.ADMIN))


@router.get("", response_model=list[PromptVariantOut], dependencies=[_admin_dep])
async def list_prompts(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[PromptVariantOut]:
    repo = PromptVariantRepo(session)
    rows = await repo.list_all()
    return [PromptVariantOut.model_validate(r) for r in rows]


@router.get("/stats", response_model=PromptVariantStats, dependencies=[_admin_dep])
async def stats(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PromptVariantStats:
    repo = PromptVariantRepo(session)
    contagem = await repo.conversas_por_variante()
    total = await repo.total_trafego_ativo()
    return PromptVariantStats(contagem=contagem, total_trafego_ativo=total)


@router.post(
    "",
    response_model=PromptVariantOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin_dep],
)
async def create_prompt(
    body: PromptVariantCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> PromptVariantOut:
    if body.nome == "default":
        raise HTTPException(
            status_code=400, detail="'default' eh reservado para o prompt hardcoded"
        )
    repo = PromptVariantRepo(session)
    if body.ativo and body.trafego_pct > 0:
        total = await repo.total_trafego_ativo(canal_slug=body.canal_slug)
        if total + body.trafego_pct > 100:
            raise HTTPException(
                status_code=400,
                detail=f"Trafego total excederia 100% (atual ativo: {total}%).",
            )
    v = PromptVariant(
        nome=body.nome,
        system_prompt=body.system_prompt,
        ativo=body.ativo,
        trafego_pct=body.trafego_pct,
        canal_slug=body.canal_slug,
        created_by=user.id,
    )
    session.add(v)
    try:
        await session.flush()
    except IntegrityError as e:
        raise HTTPException(status_code=409, detail="nome ja em uso") from e
    return PromptVariantOut.model_validate(v)


@router.patch(
    "/{variant_id}",
    response_model=PromptVariantOut,
    dependencies=[_admin_dep],
)
async def update_prompt(
    variant_id: UUID,
    body: PromptVariantUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PromptVariantOut:
    repo = PromptVariantRepo(session)
    v = await repo.get_by_id(variant_id)
    if v is None:
        raise HTTPException(status_code=404, detail="variant not found")
    new_data = body.model_dump(exclude_unset=True)
    # Valida soma de trafego se mudou trafego_pct, ativo, ou canal_slug.
    will_be_ativo = new_data.get("ativo", v.ativo)
    will_pct = new_data.get("trafego_pct", v.trafego_pct)
    will_slug = new_data.get("canal_slug", v.canal_slug)
    if will_be_ativo and will_pct > 0:
        total = await repo.total_trafego_ativo(
            canal_slug=will_slug, exclude_id=v.id
        )
        if total + will_pct > 100:
            raise HTTPException(
                status_code=400,
                detail=f"Trafego total excederia 100% (outros ativos: {total}%).",
            )
    for field, value in new_data.items():
        setattr(v, field, value)
    await session.flush()
    return PromptVariantOut.model_validate(v)
