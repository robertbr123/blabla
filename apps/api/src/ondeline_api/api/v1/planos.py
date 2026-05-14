"""CRUD /api/v1/planos — leitura/escrita sobre config['planos']."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.plano import PlanoIn, PlanoOut
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.identity import Role
from ondeline_api.deps import get_db
from ondeline_api.repositories.config import ConfigRepo

router = APIRouter(prefix="/api/v1/planos", tags=["planos"])
_admin_dep = Depends(require_role(Role.ADMIN))

_DEFAULT_PLANOS: list[dict] = [
    {
        "nome": "Essencial",
        "preco": 110.0,
        "velocidade": "35MB",
        "extras": [],
        "descricao": "",
        "ativo": True,
        "destaque": False,
    },
    {
        "nome": "Plus",
        "preco": 130.0,
        "velocidade": "55MB",
        "extras": ["IPTV gratis"],
        "descricao": "",
        "ativo": True,
        "destaque": True,
    },
    {
        "nome": "Premium",
        "preco": 150.0,
        "velocidade": "55MB",
        "extras": ["IPTV", "camera comodato"],
        "descricao": "",
        "ativo": True,
        "destaque": False,
    },
]


async def _load(repo: ConfigRepo) -> list[dict]:
    raw = await repo.get("planos")
    return list(raw) if isinstance(raw, list) else list(_DEFAULT_PLANOS)


@router.get("", response_model=list[PlanoOut])
async def list_planos(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[PlanoOut]:
    planos = await _load(ConfigRepo(session))
    return [PlanoOut(index=i, **p) for i, p in enumerate(planos)]


@router.post(
    "",
    response_model=PlanoOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin_dep],
)
async def create_plano(
    body: PlanoIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlanoOut:
    repo = ConfigRepo(session)
    planos = await _load(repo)
    data = body.model_dump()
    planos.append(data)
    await repo.set("planos", planos)
    await session.commit()
    return PlanoOut(index=len(planos) - 1, **data)


@router.patch("/{index}", response_model=PlanoOut, dependencies=[_admin_dep])
async def update_plano(
    index: int,
    body: PlanoIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlanoOut:
    repo = ConfigRepo(session)
    planos = await _load(repo)
    if index < 0 or index >= len(planos):
        raise HTTPException(status_code=404, detail="Plano not found")
    data = body.model_dump()
    planos[index] = data
    await repo.set("planos", planos)
    await session.commit()
    return PlanoOut(index=index, **data)


@router.delete("/{index}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_admin_dep])
async def delete_plano(
    index: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = ConfigRepo(session)
    planos = await _load(repo)
    if index < 0 or index >= len(planos):
        raise HTTPException(status_code=404, detail="Plano not found")
    planos.pop(index)
    await repo.set("planos", planos)
    await session.commit()
