"""GET/POST/PATCH/DELETE /api/v1/leads — gerenciamento de leads."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.deps_v1 import CursorParam, LimitParam, parse_cursor, parse_limit
from ondeline_api.api.schemas.lead import LeadCreate, LeadOut, LeadPatch
from ondeline_api.api.schemas.pagination import CursorPage, encode_cursor
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.identity import Role
from ondeline_api.deps import get_db
from ondeline_api.repositories.lead import LeadRepo

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])
_role_dep = Depends(require_role(Role.ATENDENTE, Role.ADMIN))


@router.get("", response_model=CursorPage[LeadOut], dependencies=[_role_dep])
async def list_leads(
    session: Annotated[AsyncSession, Depends(get_db)],
    cursor: CursorParam = None,
    limit: LimitParam = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query()] = None,
) -> CursorPage[LeadOut]:
    repo = LeadRepo(session)
    rows, next_cur = await repo.list_paginated(
        status=status_filter,
        q=q,
        cursor=parse_cursor(cursor),
        limit=parse_limit(limit),
    )
    items = [LeadOut.model_validate(lead) for lead in rows]
    return CursorPage[LeadOut](
        items=items, next_cursor=encode_cursor(next_cur) if next_cur else None
    )


@router.post("", response_model=LeadOut, status_code=status.HTTP_201_CREATED, dependencies=[_role_dep])
async def create_lead(
    body: LeadCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LeadOut:
    repo = LeadRepo(session)
    lead = await repo.create(
        nome=body.nome,
        whatsapp=body.whatsapp,
        interesse=body.interesse,
        atendente_id=body.atendente_id,
        notas=body.notas,
    )
    return LeadOut.model_validate(lead)


@router.get("/{lead_id}", response_model=LeadOut, dependencies=[_role_dep])
async def get_lead(
    lead_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LeadOut:
    repo = LeadRepo(session)
    lead = await repo.get_by_id(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    return LeadOut.model_validate(lead)


@router.patch("/{lead_id}", response_model=LeadOut, dependencies=[_role_dep])
async def patch_lead(
    lead_id: UUID,
    body: LeadPatch,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LeadOut:
    repo = LeadRepo(session)
    lead = await repo.get_by_id(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    await repo.update(
        lead,
        nome=body.nome,
        interesse=body.interesse,
        status=body.status,
        atendente_id=body.atendente_id,
        notas=body.notas,
    )
    return LeadOut.model_validate(lead)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_role_dep])
async def delete_lead(
    lead_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = LeadRepo(session)
    lead = await repo.get_by_id(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    await repo.delete(lead)
