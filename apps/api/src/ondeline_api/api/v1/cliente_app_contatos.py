"""Contatos da operadora — Fale conosco.

- GET cliente-app/contatos: lista publica (auth cliente) dos contatos ativos.
- CRUD admin em /api/v1/admin/cliente-app-contatos pra gestao via dashboard.
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.cliente_app import (
    ClienteAppContatoOperadora,
    ClienteAppUser,
)
from ondeline_api.db.models.identity import Role
from ondeline_api.deps import get_db

# ════════════ Cliente router ════════════

router = APIRouter(
    prefix="/api/v1/cliente-app/contatos",
    tags=["cliente-app:contatos"],
)


class ContatoOut(BaseModel):
    id: str
    tipo: str
    label: str
    valor: str
    subtitle: str | None = None
    ordem: int


class ContatosListOut(BaseModel):
    items: list[ContatoOut]


def _out(c: ClienteAppContatoOperadora) -> ContatoOut:
    return ContatoOut(
        id=str(c.id),
        tipo=c.tipo,
        label=c.label,
        valor=c.valor,
        subtitle=c.subtitle,
        ordem=c.ordem,
    )


@router.get("", response_model=ContatosListOut)
async def listar_cliente(
    _user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> ContatosListOut:
    stmt = (
        select(ClienteAppContatoOperadora)
        .where(ClienteAppContatoOperadora.ativo.is_(True))
        .order_by(asc(ClienteAppContatoOperadora.ordem))
    )
    rows = list((await session.execute(stmt)).scalars())
    return ContatosListOut(items=[_out(r) for r in rows])


# ════════════ Admin router ════════════

admin_router = APIRouter(
    prefix="/api/v1/admin/cliente-app-contatos",
    tags=["admin:cliente-app-contatos"],
)

_VALID_TIPOS = {
    "whatsapp",
    "telefone",
    "email",
    "endereco",
    "instagram",
    "facebook",
    "site",
    "outro",
}


class ContatoIn(BaseModel):
    tipo: str
    label: str = Field(min_length=1, max_length=120)
    valor: str = Field(min_length=1, max_length=2000)
    subtitle: str | None = Field(default=None, max_length=240)
    ordem: int = 0
    ativo: bool = True


class ContatoPatch(BaseModel):
    tipo: str | None = None
    label: str | None = Field(default=None, max_length=120)
    valor: str | None = Field(default=None, max_length=2000)
    subtitle: str | None = Field(default=None, max_length=240)
    ordem: int | None = None
    ativo: bool | None = None


def _validar_tipo(tipo: str) -> None:
    if tipo not in _VALID_TIPOS:
        raise HTTPException(
            status_code=400,
            detail=f"tipo invalido (use: {sorted(_VALID_TIPOS)})",
        )


class AdminContatoOut(ContatoOut):
    ativo: bool
    criado_em: str
    atualizado_em: str


def _admin_out(c: ClienteAppContatoOperadora) -> AdminContatoOut:
    return AdminContatoOut(
        id=str(c.id),
        tipo=c.tipo,
        label=c.label,
        valor=c.valor,
        subtitle=c.subtitle,
        ordem=c.ordem,
        ativo=c.ativo,
        criado_em=c.criado_em.isoformat(),
        atualizado_em=c.atualizado_em.isoformat(),
    )


@admin_router.get(
    "",
    response_model=list[AdminContatoOut],
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_listar(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[AdminContatoOut]:
    stmt = select(ClienteAppContatoOperadora).order_by(
        asc(ClienteAppContatoOperadora.ordem),
        asc(ClienteAppContatoOperadora.criado_em),
    )
    rows = list((await session.execute(stmt)).scalars())
    return [_admin_out(r) for r in rows]


@admin_router.post(
    "",
    response_model=AdminContatoOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_criar(
    body: ContatoIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminContatoOut:
    _validar_tipo(body.tipo)
    row = ClienteAppContatoOperadora(
        tipo=body.tipo,
        label=body.label,
        valor=body.valor,
        subtitle=body.subtitle,
        ordem=body.ordem,
        ativo=body.ativo,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _admin_out(row)


@admin_router.patch(
    "/{contato_id}",
    response_model=AdminContatoOut,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_patch(
    contato_id: UUID,
    body: ContatoPatch,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminContatoOut:
    row = await session.get(ClienteAppContatoOperadora, contato_id)
    if row is None:
        raise HTTPException(status_code=404, detail="contato nao encontrado")
    if body.tipo is not None:
        _validar_tipo(body.tipo)
        row.tipo = body.tipo
    if body.label is not None:
        row.label = body.label
    if body.valor is not None:
        row.valor = body.valor
    if body.subtitle is not None:
        row.subtitle = body.subtitle
    if body.ordem is not None:
        row.ordem = body.ordem
    if body.ativo is not None:
        row.ativo = body.ativo
    await session.commit()
    await session.refresh(row)
    return _admin_out(row)


@admin_router.delete(
    "/{contato_id}",
    status_code=204,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_deletar(
    contato_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    row = await session.get(ClienteAppContatoOperadora, contato_id)
    if row is None:
        raise HTTPException(status_code=404, detail="contato nao encontrado")
    await session.delete(row)
    await session.commit()
