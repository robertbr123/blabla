"""Service: atendente assume / encerra conversa."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Conversa
from ondeline_api.repositories.conversa import ConversaRepo


class ConversaNotFound(LookupError):
    pass


async def atender(
    session: AsyncSession, conversa_id: UUID, atendente_id: UUID
) -> Conversa:
    repo = ConversaRepo(session)
    c = await repo.get_by_id(conversa_id)
    if c is None:
        raise ConversaNotFound(str(conversa_id))
    await repo.assign_atendente(c, atendente_id)
    return c


async def encerrar(session: AsyncSession, conversa_id: UUID) -> Conversa:
    repo = ConversaRepo(session)
    c = await repo.get_by_id(conversa_id)
    if c is None:
        raise ConversaNotFound(str(conversa_id))
    await repo.encerrar(c)
    return c
