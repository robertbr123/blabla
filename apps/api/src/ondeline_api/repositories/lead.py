"""LeadRepo — CRUD + filtered pagination."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Lead, LeadStatus


class LeadRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, lead_id: UUID) -> Lead | None:
        stmt = select(Lead).where(Lead.id == lead_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_paginated(
        self,
        *,
        status: str | None = None,
        q: str | None = None,
        cursor: datetime | None = None,
        limit: int = 50,
    ) -> tuple[list[Lead], datetime | None]:
        stmt = select(Lead)
        if status:
            stmt = stmt.where(Lead.status == LeadStatus(status))
        if q:
            stmt = stmt.where(Lead.nome.ilike(f"%{q}%"))
        if cursor is not None:
            stmt = stmt.where(Lead.created_at < cursor)
        stmt = stmt.order_by(desc(Lead.created_at)).limit(limit + 1)
        rows = list((await self._session.execute(stmt)).scalars().all())
        if len(rows) > limit:
            next_cursor = rows[limit].created_at
            rows = rows[:limit]
        else:
            next_cursor = None
        return rows, next_cursor

    async def create(
        self,
        *,
        nome: str,
        whatsapp: str,
        interesse: str | None = None,
        atendente_id: UUID | None = None,
        notas: str | None = None,
    ) -> Lead:
        lead = Lead(
            nome=nome,
            whatsapp=whatsapp,
            interesse=interesse,
            status=LeadStatus.NOVO,
            atendente_id=atendente_id,
            notas=notas,
        )
        self._session.add(lead)
        await self._session.flush()
        return lead

    async def update(
        self,
        lead: Lead,
        *,
        nome: str | None = None,
        interesse: str | None = None,
        status: str | None = None,
        atendente_id: UUID | None = None,
        notas: str | None = None,
    ) -> None:
        if nome is not None:
            lead.nome = nome
        if interesse is not None:
            lead.interesse = interesse
        if status is not None:
            lead.status = LeadStatus(status)
        if atendente_id is not None:
            lead.atendente_id = atendente_id
        if notas is not None:
            lead.notas = notas
        await self._session.flush()
        await self._session.refresh(lead)

    async def delete(self, lead: Lead) -> None:
        await self._session.delete(lead)
        await self._session.flush()
