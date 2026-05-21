"""Router /api/v1/cliente-app/os — abertura e listagem de chamados pelo cliente."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.cliente_app_auth import (
    OsCreateIn,
    OsListOut,
    OsOut,
)
from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.db.models.cliente_app import ClienteAppOs, ClienteAppUser
from ondeline_api.deps import get_db

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
