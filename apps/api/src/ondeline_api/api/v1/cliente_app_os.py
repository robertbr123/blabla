"""Routers do dominio cliente-app OS.

- `/api/v1/cliente-app/os` — endpoints que o cliente acessa (lista propria, cria, detalhe).
- `/api/v1/admin/cliente-app-os` — endpoints admin no dashboard (lista todas, atualiza status).
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.cliente_app_auth import (
    OsCreateIn,
    OsListOut,
    OsOut,
)
from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.cliente_app import ClienteAppOs, ClienteAppUser
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db

log = structlog.get_logger(__name__)

# ════════════════════════ Cliente router ════════════════════════

router = APIRouter(prefix="/api/v1/cliente-app/os", tags=["cliente-app:os"])


def _os_out(o: ClienteAppOs) -> OsOut:
    return OsOut(
        id=str(o.id),
        tipo=o.tipo,
        descricao=o.descricao,
        status=o.status,
        created_at=o.created_at.isoformat(),
        updated_at=o.updated_at.isoformat(),
    )


@router.get("", response_model=OsListOut)
async def listar(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> OsListOut:
    stmt = (
        select(ClienteAppOs)
        .where(ClienteAppOs.cliente_app_user_id == user.id)
        .order_by(desc(ClienteAppOs.created_at))
    )
    rows = (await session.execute(stmt)).scalars().all()
    return OsListOut(items=[_os_out(r) for r in rows])


@router.post("", response_model=OsOut, status_code=201)
async def criar(
    body: OsCreateIn,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> OsOut:
    os_row = ClienteAppOs(
        cliente_app_user_id=user.id,
        tipo=body.tipo,
        descricao=body.descricao,
        payload_json=body.payload,
        status="aberto",
    )
    session.add(os_row)
    await session.flush()
    await session.commit()
    await session.refresh(os_row)
    return _os_out(os_row)


@router.get("/{os_id}", response_model=OsOut)
async def detalhe(
    os_id: UUID,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> OsOut:
    row = await session.get(ClienteAppOs, os_id)
    if row is None or row.cliente_app_user_id != user.id:
        raise HTTPException(status_code=404, detail="chamado nao encontrado")
    return _os_out(row)


# ════════════════════════ Admin router ════════════════════════

admin_router = APIRouter(
    prefix="/api/v1/admin/cliente-app-os",
    tags=["admin:cliente-app-os"],
)


class AdminOsItemOut(BaseModel):
    id: str
    tipo: str
    descricao: str
    payload: dict
    status: str
    sgp_protocolo_id: str | None
    atendente_user_id: str | None
    atendente_nome: str | None
    cliente_app_user_id: str
    cliente_nome: str
    cliente_cpf_last4: str
    cliente_telefone: str
    cliente_email: str | None
    created_at: str
    updated_at: str


class AdminOsListOut(BaseModel):
    items: list[AdminOsItemOut]
    total: int
    counts_by_status: dict[str, int]


class AdminOsPatchIn(BaseModel):
    status: str | None = None
    sgp_protocolo_id: str | None = None
    assign_to_me: bool = False

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: str | None) -> str | None:
        if v is None:
            return None
        allowed = {"aberto", "em_atendimento", "concluido", "cancelado"}
        if v not in allowed:
            raise ValueError(f"status invalido (use: {sorted(allowed)})")
        return v


def _admin_item(o: ClienteAppOs, u: ClienteAppUser, atendente: User | None) -> AdminOsItemOut:
    return AdminOsItemOut(
        id=str(o.id),
        tipo=o.tipo,
        descricao=o.descricao,
        payload=o.payload_json or {},
        status=o.status,
        sgp_protocolo_id=o.sgp_protocolo_id,
        atendente_user_id=str(o.atendente_user_id) if o.atendente_user_id else None,
        atendente_nome=atendente.nome if atendente else None,
        cliente_app_user_id=str(u.id),
        cliente_nome=decrypt_pii(u.nome_encrypted) if u.nome_encrypted else "",
        cliente_cpf_last4=u.cpf_last4,
        cliente_telefone=decrypt_pii(u.telefone_encrypted) if u.telefone_encrypted else "",
        cliente_email=decrypt_pii(u.email_encrypted) if u.email_encrypted else None,
        created_at=o.created_at.isoformat(),
        updated_at=o.updated_at.isoformat(),
    )


@admin_router.get(
    "",
    response_model=AdminOsListOut,
    dependencies=[Depends(require_role(Role.ATENDENTE, Role.ADMIN))],
)
async def admin_listar(
    status: Annotated[str | None, Query()] = None,
    tipo: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> AdminOsListOut:
    stmt = select(ClienteAppOs)
    if status:
        stmt = stmt.where(ClienteAppOs.status == status)
    if tipo:
        stmt = stmt.where(ClienteAppOs.tipo == tipo)
    stmt = stmt.order_by(desc(ClienteAppOs.created_at)).limit(limit).offset(offset)
    rows = list((await session.execute(stmt)).scalars())

    # users + atendentes
    user_ids = list({r.cliente_app_user_id for r in rows})
    atendente_ids = list({r.atendente_user_id for r in rows if r.atendente_user_id})
    users_map: dict = {}
    if user_ids:
        u_stmt = select(ClienteAppUser).where(ClienteAppUser.id.in_(user_ids))
        users_map = {u.id: u for u in (await session.execute(u_stmt)).scalars()}
    atend_map: dict = {}
    if atendente_ids:
        a_stmt = select(User).where(User.id.in_(atendente_ids))
        atend_map = {u.id: u for u in (await session.execute(a_stmt)).scalars()}

    items = [
        _admin_item(r, users_map[r.cliente_app_user_id], atend_map.get(r.atendente_user_id))
        for r in rows
        if r.cliente_app_user_id in users_map
    ]

    # Total (sem filtros de paginacao, mas com filtros de status/tipo)
    total_stmt = select(func.count()).select_from(ClienteAppOs)
    if status:
        total_stmt = total_stmt.where(ClienteAppOs.status == status)
    if tipo:
        total_stmt = total_stmt.where(ClienteAppOs.tipo == tipo)
    total = int((await session.execute(total_stmt)).scalar() or 0)

    # Counts por status (sem nenhum filtro, pra cards do header)
    counts_stmt = select(ClienteAppOs.status, func.count()).group_by(ClienteAppOs.status)
    counts_by_status = {s: int(c) for s, c in (await session.execute(counts_stmt)).all()}

    return AdminOsListOut(items=items, total=total, counts_by_status=counts_by_status)


@admin_router.get(
    "/{os_id}",
    response_model=AdminOsItemOut,
    dependencies=[Depends(require_role(Role.ATENDENTE, Role.ADMIN))],
)
async def admin_detalhe(
    os_id: UUID,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> AdminOsItemOut:
    o = await session.get(ClienteAppOs, os_id)
    if o is None:
        raise HTTPException(status_code=404, detail="chamado nao encontrado")
    u = await session.get(ClienteAppUser, o.cliente_app_user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="cliente do chamado nao encontrado")
    atendente = (
        await session.get(User, o.atendente_user_id) if o.atendente_user_id else None
    )
    return _admin_item(o, u, atendente)


@admin_router.patch(
    "/{os_id}",
    response_model=AdminOsItemOut,
)
async def admin_patch(
    os_id: UUID,
    body: AdminOsPatchIn,
    current_user: User = Depends(require_role(Role.ATENDENTE, Role.ADMIN)),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> AdminOsItemOut:
    o = await session.get(ClienteAppOs, os_id)
    if o is None:
        raise HTTPException(status_code=404, detail="chamado nao encontrado")

    if body.status is not None:
        o.status = body.status
    if body.sgp_protocolo_id is not None:
        o.sgp_protocolo_id = body.sgp_protocolo_id or None
    if body.assign_to_me:
        o.atendente_user_id = current_user.id

    await session.flush()
    await session.commit()
    await session.refresh(o)

    u = await session.get(ClienteAppUser, o.cliente_app_user_id)
    assert u is not None
    atendente = (
        await session.get(User, o.atendente_user_id) if o.atendente_user_id else None
    )
    return _admin_item(o, u, atendente)
