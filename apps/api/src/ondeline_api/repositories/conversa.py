"""Repositorio de Conversa — queries e mutacoes encapsuladas."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import (
    Cliente,
    Conversa,
    ConversaEstado,
    ConversaStatus,
    Mensagem,
)


class ConversaRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_by_whatsapp(
        self, whatsapp: str, *, canal_id: UUID | None = None
    ) -> Conversa:
        """Devolve a conversa aberta para (whatsapp, canal_id), criando se faltar.

        F4: conversas sao escopadas por canal — o mesmo cliente em 2 canais
        diferentes gera 2 conversas independentes. ``canal_id=None`` casa
        apenas com conversas legadas sem canal atribuido (compat backward).
        """
        stmt = (
            select(Conversa)
            .where(Conversa.whatsapp == whatsapp, Conversa.deleted_at.is_(None))
        )
        if canal_id is None:
            stmt = stmt.where(Conversa.canal_id.is_(None))
        else:
            stmt = stmt.where(Conversa.canal_id == canal_id)
        stmt = stmt.order_by(Conversa.created_at.desc()).limit(1)
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return existing

        conversa = Conversa(whatsapp=whatsapp, canal_id=canal_id)
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
        canal_id: UUID | None = None,
        cursor: datetime | None = None,
        limit: int = 50,
    ) -> tuple[list[tuple[Conversa, str | None]], datetime | None]:
        """List open conversas, newest first by last_message_at (or created_at).

        Returns tuples ``(conversa, nome_encrypted)`` — the caller decrypts.
        Implementado com 2 queries (conversas + clientes IN ids) ao inves de
        JOIN para evitar ambiguidade de FROM no SQLAlchemy. O segundo SELECT
        traz no maximo ``limit`` ids unicos, custo desprezivel.
        """
        from sqlalchemy import case, desc

        stmt = select(Conversa).where(Conversa.deleted_at.is_(None))
        if status:
            stmt = stmt.where(Conversa.status == status)
        if q:
            stmt = stmt.where(Conversa.whatsapp.ilike(f"%{q}%"))
        if canal_id is not None:
            stmt = stmt.where(Conversa.canal_id == canal_id)
        # cidade filter requires join with Cliente — skip for M6 v1 baseline
        order_col = case(
            (Conversa.last_message_at.is_(None), Conversa.created_at),
            else_=Conversa.last_message_at,
        )
        if cursor is not None:
            stmt = stmt.where(order_col < cursor)
        stmt = stmt.order_by(desc(order_col)).limit(limit + 1)
        conversas = list((await self._session.execute(stmt)).scalars().all())
        if len(conversas) > limit:
            next_item = conversas[limit]
            next_cursor = next_item.last_message_at or next_item.created_at
            conversas = conversas[:limit]
        else:
            next_cursor = None

        cliente_ids = {c.cliente_id for c in conversas if c.cliente_id is not None}
        nomes: dict[UUID, str | None] = {}
        if cliente_ids:
            cstmt = select(Cliente.id, Cliente.nome_encrypted).where(
                Cliente.id.in_(cliente_ids)
            )
            for cid, nome_enc in (await self._session.execute(cstmt)).all():
                nomes[cid] = nome_enc

        return [
            (c, nomes.get(c.cliente_id) if c.cliente_id is not None else None)
            for c in conversas
        ], next_cursor

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
        """Encerra o atendimento humano e DEVOLVE o controle pro bot.

        Em vez de marcar como ENCERRADA (que bloqueava o bot de responder
        próximas mensagens, forçando o cliente a apagar a conversa pra reativar),
        a conversa volta pro estado neutro CLIENTE/BOT. Histórico é preservado
        (não há soft-delete). Atendente é desassociado.
        """
        conversa.status = ConversaStatus.BOT
        conversa.estado = ConversaEstado.CLIENTE
        conversa.atendente_id = None
        conversa.transferred_at = None
        conversa.first_response_at = None
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
