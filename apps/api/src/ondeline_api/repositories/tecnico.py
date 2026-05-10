"""TecnicoRepo: roteamento por (cidade, rua) com prioridade."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Tecnico, TecnicoArea


class TecnicoRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_area(self, *, cidade: str, rua: str) -> Tecnico | None:
        cidade_lc = (cidade or "").strip().lower()
        rua_lc = (rua or "").strip().lower()
        stmt = (
            select(Tecnico, TecnicoArea)
            .join(TecnicoArea, TecnicoArea.tecnico_id == Tecnico.id)
            .where(Tecnico.ativo.is_(True))
            .order_by(TecnicoArea.prioridade.asc())
        )
        rows = (await self._session.execute(stmt)).all()
        # ranking simples: prioridade baixa primeiro; tie-break por match exato cidade+rua > so cidade
        best: Tecnico | None = None
        best_score = -1
        for tec, area in rows:
            score = 0
            if (area.cidade or "").lower() == cidade_lc:
                score += 2
            if (area.rua or "").lower() == rua_lc:
                score += 3
            if score > best_score:
                best = tec
                best_score = score
        return best
