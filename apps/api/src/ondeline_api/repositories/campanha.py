# apps/api/src/ondeline_api/repositories/campanha.py
"""CampanhaRepo — CRUD de campanhas + agregação de status dos destinatários."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Campanha, CampanhaDestinatario


class CampanhaRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Campanha]:
        stmt = select(Campanha).order_by(Campanha.created_at.desc())
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_by_id(self, campanha_id: UUID) -> Campanha | None:
        stmt = select(Campanha).where(Campanha.id == campanha_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def status_counts(self, campanha_id: UUID) -> dict[str, int]:
        """Conta destinatários por status (pendente/enviada/entregue/lida/falha)."""
        stmt = (
            select(CampanhaDestinatario.status, func.count())
            .where(CampanhaDestinatario.campanha_id == campanha_id)
            .group_by(CampanhaDestinatario.status)
        )
        rows = (await self._session.execute(stmt)).all()
        return {str(status): int(n) for status, n in rows}
