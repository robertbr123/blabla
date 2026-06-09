"""Repositorio de Mensagem — insercao idempotente para inbound, write-only para bot."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.crypto import encrypt_pii
from ondeline_api.db.models.business import Mensagem, MensagemRole


class MensagemRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_inbound_or_skip(
        self,
        *,
        conversa_id: UUID,
        external_id: str,
        text: str | None,
        media_type: str | None,
        media_url: str | None,
    ) -> Mensagem | None:
        """Insere mensagem do cliente. Retorna None se duplicada (UNIQUE em external_id).

        UNIQUE parcial criado em M2: `ix_mensagens_external (external_id, created_at)
        WHERE external_id IS NOT NULL`. Ao colidir, usamos savepoint (begin_nested)
        para isolar o rollback e preservar a transacao pai.
        """
        msg = Mensagem(
            conversa_id=conversa_id,
            external_id=external_id,
            role=MensagemRole.CLIENTE,
            content_encrypted=encrypt_pii(text) if text else None,
            media_type=media_type,
            media_url=media_url,
        )
        async with self._session.begin_nested() as savepoint:
            self._session.add(msg)
            try:
                await savepoint.session.flush()
            except IntegrityError:
                await savepoint.rollback()
                return None
        return msg

    async def exists_by_external_id(self, external_id: str) -> bool:
        """True se ja existe mensagem com esse external_id (dedup de re-entrega).

        Usa o indice parcial ix_mensagens_external (external_id e a coluna lider).
        Retry-safe: so enxerga linhas commitadas; tentativa que deu rollback nao
        aparece, logo o retry reprocessa.

        Filtra a janela recente (24h): re-entregas/retries sao sempre recentes, e
        o predicado em created_at permite partition pruning (nao varre todas as
        particoes mensais).
        """
        recente = datetime.now(tz=UTC) - timedelta(hours=24)
        result = await self._session.execute(
            select(Mensagem.id)
            .where(Mensagem.external_id == external_id, Mensagem.created_at > recente)
            .limit(1)
        )
        return result.first() is not None

    async def list_history(
        self, conversa_id: UUID, *, limit: int = 12
    ) -> list[Mensagem]:
        from sqlalchemy import select

        stmt = (
            select(Mensagem)
            .where(Mensagem.conversa_id == conversa_id)
            .order_by(Mensagem.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return list(reversed(rows))

    async def insert_bot_reply(
        self,
        *,
        conversa_id: UUID,
        text: str,
    ) -> Mensagem:
        msg = Mensagem(
            conversa_id=conversa_id,
            external_id=None,
            role=MensagemRole.BOT,
            content_encrypted=encrypt_pii(text),
        )
        self._session.add(msg)
        await self._session.flush()
        return msg
