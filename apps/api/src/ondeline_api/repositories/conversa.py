"""Repositorio de Conversa — queries e mutacoes encapsuladas."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
    Mensagem,
)


class ConversaRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_by_whatsapp(self, whatsapp: str) -> Conversa:
        """Devolve a conversa aberta (deleted_at IS NULL) para esse whatsapp,
        criando se nao existir. Faz flush imediato para garantir id presente.
        """
        stmt = (
            select(Conversa)
            .where(Conversa.whatsapp == whatsapp, Conversa.deleted_at.is_(None))
            .order_by(Conversa.created_at.desc())
            .limit(1)
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return existing

        conversa = Conversa(whatsapp=whatsapp)
        self._session.add(conversa)
        await self._session.flush()
        return conversa

    async def update_estado_status(
        self,
        conversa: Conversa,
        *,
        estado: ConversaEstado,
        status: ConversaStatus,
    ) -> None:
        conversa.estado = estado
        conversa.status = status
        conversa.last_message_at = datetime.now(tz=UTC)
        await self._session.flush()

    async def set_cliente(self, conversa: Conversa, cliente_id: UUID) -> None:
        conversa.cliente_id = cliente_id
        await self._session.flush()

    async def add_tag(self, conversa: Conversa, tag: str) -> None:
        current: list[str] = conversa.tags or []
        if tag not in current:
            conversa.tags = [*current, tag]
            await self._session.flush()

    async def list_paginated(
        self,
        *,
        status: str | None = None,
        cidade: str | None = None,
        q: str | None = None,
        cursor: datetime | None = None,
        limit: int = 50,
    ) -> tuple[list[Conversa], datetime | None]:
        """List open conversas, newest first by last_message_at (or created_at)."""
        from sqlalchemy import case, desc

        stmt = select(Conversa).where(Conversa.deleted_at.is_(None))
        if status:
            stmt = stmt.where(Conversa.status == status)
        if q:
            stmt = stmt.where(Conversa.whatsapp.ilike(f"%{q}%"))
        # cidade filter requires join with Cliente — skip for M6 v1 baseline
        order_col = case(
            (Conversa.last_message_at.is_(None), Conversa.created_at),
            else_=Conversa.last_message_at,
        )
        if cursor is not None:
            stmt = stmt.where(order_col < cursor)
        stmt = stmt.order_by(desc(order_col)).limit(limit + 1)
        rows = list((await self._session.execute(stmt)).scalars().all())
        if len(rows) > limit:
            next_item = rows[limit]
            next_cursor = next_item.last_message_at or next_item.created_at
            rows = rows[:limit]
        else:
            next_cursor = None
        return rows, next_cursor

    async def get_by_id(self, conversa_id: UUID) -> Conversa | None:
        stmt = select(Conversa).where(
            Conversa.id == conversa_id, Conversa.deleted_at.is_(None)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_messages(
        self,
        conversa_id: UUID,
        *,
        cursor: datetime | None = None,
        limit: int = 50,
    ) -> tuple[list[Mensagem], datetime | None]:
        from sqlalchemy import desc

        stmt = select(Mensagem).where(Mensagem.conversa_id == conversa_id)
        if cursor is not None:
            stmt = stmt.where(Mensagem.created_at < cursor)
        stmt = stmt.order_by(desc(Mensagem.created_at)).limit(limit + 1)
        rows = list((await self._session.execute(stmt)).scalars().all())
        if len(rows) > limit:
            next_cursor = rows[limit].created_at
            rows = rows[:limit]
        else:
            next_cursor = None
        # return in chronological order (oldest first) for display
        return list(reversed(rows)), next_cursor

    async def soft_delete(self, conversa: Conversa) -> None:
        from datetime import timedelta

        now = datetime.now(tz=UTC)
        conversa.deleted_at = now
        conversa.retention_until = now + timedelta(days=30)
        await self._session.flush()

    async def assign_atendente(
        self, conversa: Conversa, atendente_id: UUID
    ) -> None:
        conversa.atendente_id = atendente_id
        conversa.status = ConversaStatus.HUMANO
        conversa.estado = ConversaEstado.HUMANO
        await self._session.flush()

    async def encerrar(self, conversa: Conversa) -> None:
        conversa.status = ConversaStatus.ENCERRADA
        conversa.estado = ConversaEstado.ENCERRADA
        await self._session.flush()

    async def find_active_by_cliente_id(self, cliente_id: UUID) -> Conversa | None:
        """Returns the most recent non-encerrada conversa for a client."""
        from sqlalchemy import desc

        stmt = (
            select(Conversa)
            .where(
                Conversa.cliente_id == cliente_id,
                Conversa.deleted_at.is_(None),
                Conversa.status != ConversaStatus.ENCERRADA,
            )
            .order_by(desc(Conversa.created_at))
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()
