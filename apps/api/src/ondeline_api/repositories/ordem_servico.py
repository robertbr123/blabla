"""OrdemServicoRepo — CRUD operations."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import OrdemServico, OsStatus


class OrdemServicoRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        codigo: str,
        cliente_id: UUID,
        tecnico_id: UUID | None,
        problema: str,
        endereco: str,
    ) -> OrdemServico:
        os_ = OrdemServico(
            codigo=codigo,
            cliente_id=cliente_id,
            tecnico_id=tecnico_id,
            problema=problema,
            endereco=endereco,
            status=OsStatus.PENDENTE,
        )
        self._session.add(os_)
        await self._session.flush()
        return os_

    async def get_by_id(self, os_id: UUID) -> OrdemServico | None:
        from sqlalchemy import select

        stmt = select(OrdemServico).where(OrdemServico.id == os_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_paginated(
        self,
        *,
        status: str | None = None,
        tecnico_id: UUID | None = None,
        cliente_id: UUID | None = None,
        cidade: str | None = None,  # filter via Cliente.cidade join
        cursor: datetime | None = None,
        limit: int = 50,
    ) -> tuple[list[OrdemServico], datetime | None]:
        from sqlalchemy import desc, select

        stmt = select(OrdemServico)
        if status:
            stmt = stmt.where(OrdemServico.status == status)
        if tecnico_id:
            stmt = stmt.where(OrdemServico.tecnico_id == tecnico_id)
        if cliente_id:
            stmt = stmt.where(OrdemServico.cliente_id == cliente_id)
        if cursor is not None:
            stmt = stmt.where(OrdemServico.criada_em < cursor)
        stmt = stmt.order_by(desc(OrdemServico.criada_em)).limit(limit + 1)
        rows = list((await self._session.execute(stmt)).scalars().all())
        if len(rows) > limit:
            next_cursor = rows[limit].criada_em
            rows = rows[:limit]
        else:
            next_cursor = None
        return rows, next_cursor

    async def update(
        self,
        os_: OrdemServico,
        *,
        status: str | None = None,
        tecnico_id: UUID | None = None,
        agendamento_at: datetime | None = None,
    ) -> None:
        if status is not None:
            os_.status = OsStatus(status)
        if tecnico_id is not None:
            os_.tecnico_id = tecnico_id
        if agendamento_at is not None:
            os_.agendamento_at = agendamento_at
        await self._session.flush()

    async def add_foto(self, os_: OrdemServico, foto_meta: dict[str, Any]) -> None:
        existing = list(os_.fotos or [])
        existing.append(foto_meta)
        os_.fotos = existing
        await self._session.flush()

    async def list_for_tecnico(
        self,
        tecnico_id: UUID,
        *,
        status_filter: str | None = None,
    ) -> list[OrdemServico]:
        """List OS assigned to tecnico. By default excludes concluida/cancelada."""
        from sqlalchemy import desc, select

        stmt = select(OrdemServico).where(OrdemServico.tecnico_id == tecnico_id)
        if status_filter:
            stmt = stmt.where(OrdemServico.status == OsStatus(status_filter))
        else:
            stmt = stmt.where(
                OrdemServico.status.in_([OsStatus.PENDENTE, OsStatus.EM_ANDAMENTO])
            )
        stmt = stmt.order_by(desc(OrdemServico.criada_em))
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_by_id_and_tecnico(
        self, os_id: UUID, tecnico_id: UUID
    ) -> OrdemServico | None:
        from sqlalchemy import select

        stmt = select(OrdemServico).where(
            OrdemServico.id == os_id, OrdemServico.tecnico_id == tecnico_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def set_iniciada_with_gps(
        self,
        os_: OrdemServico,
        *,
        lat: float | None = None,
        lng: float | None = None,
    ) -> None:
        os_.status = OsStatus.EM_ANDAMENTO
        if lat is not None:
            os_.gps_inicio_lat = lat
        if lng is not None:
            os_.gps_inicio_lng = lng
        await self._session.flush()

    async def set_concluida_with_gps(
        self,
        os_: OrdemServico,
        *,
        csat: int | None = None,
        comentario: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
    ) -> None:
        from datetime import UTC, datetime

        os_.status = OsStatus.CONCLUIDA
        os_.concluida_em = datetime.now(tz=UTC)
        if csat is not None:
            os_.csat = csat
        if comentario is not None:
            os_.comentario_cliente = comentario
        if lat is not None:
            os_.gps_fim_lat = lat
        if lng is not None:
            os_.gps_fim_lng = lng
        await self._session.flush()

    async def concluir(
        self,
        os_: OrdemServico,
        *,
        csat: int | None = None,
        comentario: str | None = None,
    ) -> None:
        from datetime import UTC
        from datetime import datetime as _datetime

        os_.status = OsStatus.CONCLUIDA
        os_.concluida_em = _datetime.now(tz=UTC)
        if csat is not None:
            os_.csat = csat
        if comentario is not None:
            os_.comentario_cliente = comentario
        await self._session.flush()
