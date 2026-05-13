"""ManutencaoRepo — list_active_in_cidade + CRUD."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, select
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

    async def get_by_id(self, manutencao_id: UUID) -> Manutencao | None:
        stmt = select(Manutencao).where(Manutencao.id == manutencao_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_paginated(
        self,
        *,
        ativas: bool | None = None,
        cursor: datetime | None = None,
        limit: int = 50,
    ) -> tuple[list[Manutencao], datetime | None]:
        stmt = select(Manutencao)
        if ativas:
            now = datetime.now(tz=UTC)
            stmt = stmt.where(Manutencao.inicio_at <= now, Manutencao.fim_at >= now)
        if cursor is not None:
            stmt = stmt.where(Manutencao.inicio_at < cursor)
        stmt = stmt.order_by(desc(Manutencao.inicio_at)).limit(limit + 1)
        rows = list((await self._session.execute(stmt)).scalars().all())
        if len(rows) > limit:
            next_cursor = rows[limit].inicio_at
            rows = rows[:limit]
        else:
            next_cursor = None
        return rows, next_cursor

    async def create(
        self,
        *,
        titulo: str,
        descricao: str | None,
        inicio_at: datetime,
        fim_at: datetime,
        cidades: list[str] | None,
        notificar: bool,
    ) -> Manutencao:
        m = Manutencao(
            titulo=titulo,
            descricao=descricao,
            inicio_at=inicio_at,
            fim_at=fim_at,
            cidades=cidades,
            notificar=notificar,
        )
        self._session.add(m)
        await self._session.flush()
        return m

    async def update(
        self,
        m: Manutencao,
        *,
        titulo: str | None = None,
        descricao: str | None = None,
        inicio_at: datetime | None = None,
        fim_at: datetime | None = None,
        cidades: list[str] | None = None,
        notificar: bool | None = None,
    ) -> None:
        if titulo is not None:
            m.titulo = titulo
        if descricao is not None:
            m.descricao = descricao
        if inicio_at is not None:
            m.inicio_at = inicio_at
        if fim_at is not None:
            m.fim_at = fim_at
        if cidades is not None:
            m.cidades = cidades
        if notificar is not None:
            m.notificar = notificar
        await self._session.flush()

    async def delete(self, m: Manutencao) -> None:
        await self._session.delete(m)
        await self._session.flush()
