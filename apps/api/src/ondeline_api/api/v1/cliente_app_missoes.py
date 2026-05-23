"""Endpoint GET /missoes — lista status atual das missoes do user."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.deps import get_db
from ondeline_api.services.missoes import status_missoes

router = APIRouter(
    prefix="/api/v1/cliente-app",
    tags=["cliente-app:missoes"],
)


class MissaoItemOut(BaseModel):
    slug: str
    titulo: str
    descricao: str
    pontos: int
    periodicidade: str  # 'diaria' | 'por_os' | 'on_the_fly'
    icon: str
    completada_hoje: bool
    total_concluida: int


class MissoesOut(BaseModel):
    items: list[MissaoItemOut]


@router.get("/missoes", response_model=MissoesOut)
async def get_missoes(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> MissoesOut:
    items = await status_missoes(session, user)
    return MissoesOut(items=[MissaoItemOut(**it) for it in items])
