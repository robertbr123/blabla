"""ManutencaoRepo — list_active_in_cidade."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Manutencao


class ManutencaoRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_in_cidade(self, cidade: str) -> list[Manutencao]:
        now = datetime.now(tz=UTC)
        stmt = select(Manutencao).where(
            Manutencao.inicio_at <= now,
            Manutencao.fim_at >= now,
        )
        all_active = (await self._session.execute(stmt)).scalars().all()
        cidade_lc = (cidade or "").strip().lower()
        if not cidade_lc:
            return list(all_active)
        return [
            m for m in all_active
            if m.cidades is None
            or any(c.strip().lower() == cidade_lc for c in (m.cidades or []))
        ]
