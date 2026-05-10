"""NotificacaoRepo — CRUD + dedup por (cliente_id, tipo, agendada_para)."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import (
    Notificacao,
    NotificacaoStatus,
    NotificacaoTipo,
)


class NotificacaoRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def already_scheduled(
        self,
        *,
        cliente_id: UUID,
        tipo: NotificacaoTipo,
        agendada_para: datetime,
    ) -> bool:
        stmt = select(Notificacao.id).where(
            and_(
                Notificacao.cliente_id == cliente_id,
                Notificacao.tipo == tipo,
                Notificacao.agendada_para == agendada_para,
            )
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def schedule(
        self,
        *,
        cliente_id: UUID,
        tipo: NotificacaoTipo,
        agendada_para: datetime,
        payload: dict[str, Any],
    ) -> Notificacao | None:
        if await self.already_scheduled(
            cliente_id=cliente_id, tipo=tipo, agendada_para=agendada_para
        ):
            return None
        n = Notificacao(
            cliente_id=cliente_id,
            tipo=tipo,
            agendada_para=agendada_para,
            payload=payload,
            status=NotificacaoStatus.PENDENTE,
        )
        self._session.add(n)
        await self._session.flush()
        return n

    async def list_due(self, *, now: datetime, limit: int = 100) -> list[Notificacao]:
        stmt = (
            select(Notificacao)
            .where(
                Notificacao.status == NotificacaoStatus.PENDENTE,
                Notificacao.agendada_para <= now,
            )
            .order_by(Notificacao.agendada_para)
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def mark_sent(self, n: Notificacao) -> None:
        n.status = NotificacaoStatus.ENVIADA
        n.enviada_em = datetime.now(tz=UTC)
        await self._session.flush()

    async def mark_failed(self, n: Notificacao) -> None:
        n.tentativas += 1
        if n.tentativas >= 3:
            n.status = NotificacaoStatus.FALHA
        await self._session.flush()
