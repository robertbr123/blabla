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
