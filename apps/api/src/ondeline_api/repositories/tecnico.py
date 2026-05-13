"""TecnicoRepo: roteamento por (cidade, rua) com prioridade."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Tecnico, TecnicoArea


class TecnicoRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, tecnico_id: UUID) -> Tecnico | None:
        stmt = select(Tecnico).where(Tecnico.id == tecnico_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_paginated(
        self,
        *,
        ativo: bool | None = None,
        cursor: UUID | None = None,
        limit: int = 50,
    ) -> tuple[list[Tecnico], UUID | None]:
        """Tecnicos paginated by id (no created_at column)."""
        stmt = select(Tecnico)
        if ativo is not None:
            stmt = stmt.where(Tecnico.ativo == ativo)
        if cursor is not None:
            stmt = stmt.where(Tecnico.id > cursor)
        stmt = stmt.order_by(Tecnico.id).limit(limit + 1)
        rows = list((await self._session.execute(stmt)).scalars().all())
        if len(rows) > limit:
            next_cursor: UUID | None = rows[limit].id
            rows = rows[:limit]
        else:
            next_cursor = None
        return rows, next_cursor

    async def create(
        self,
        *,
        nome: str,
        whatsapp: str | None = None,
        ativo: bool = True,
        user_id: UUID | None = None,
    ) -> Tecnico:
        tec = Tecnico(nome=nome, whatsapp=whatsapp, ativo=ativo, user_id=user_id)
        self._session.add(tec)
        await self._session.flush()
        return tec

    async def update(
        self,
        tec: Tecnico,
        *,
        nome: str | None = None,
        whatsapp: str | None = None,
        ativo: bool | None = None,
        gps_lat: float | None = None,
        gps_lng: float | None = None,
    ) -> None:
        if nome is not None:
            tec.nome = nome
        if whatsapp is not None:
            tec.whatsapp = whatsapp
        if ativo is not None:
            tec.ativo = ativo
        if gps_lat is not None and gps_lng is not None:
            from datetime import UTC, datetime

            tec.gps_lat = gps_lat
            tec.gps_lng = gps_lng
            tec.gps_ts = datetime.now(tz=UTC)
        await self._session.flush()

    async def delete(self, tec: Tecnico) -> None:
        await self._session.delete(tec)
        await self._session.flush()

    async def list_areas(self, tecnico_id: UUID) -> list[TecnicoArea]:
        stmt = select(TecnicoArea).where(TecnicoArea.tecnico_id == tecnico_id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def add_area(
        self, tecnico_id: UUID, *, cidade: str, rua: str, prioridade: int = 1
    ) -> TecnicoArea:
        area = TecnicoArea(
            tecnico_id=tecnico_id, cidade=cidade, rua=rua, prioridade=prioridade
        )
        self._session.add(area)
        await self._session.flush()
        return area

    async def remove_area(self, tecnico_id: UUID, cidade: str, rua: str) -> bool:
        from sqlalchemy import delete
        from sqlalchemy.engine import CursorResult

        stmt = delete(TecnicoArea).where(
            TecnicoArea.tecnico_id == tecnico_id,
            TecnicoArea.cidade == cidade,
            TecnicoArea.rua == rua,
        )
        result: CursorResult[Any] = await self._session.execute(stmt)  # type: ignore[assignment]
        await self._session.flush()
        return (result.rowcount or 0) > 0

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
