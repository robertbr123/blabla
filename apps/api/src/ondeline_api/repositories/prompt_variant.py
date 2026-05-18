"""Repo de PromptVariant (F5)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Conversa, PromptVariant


class PromptVariantRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_id(self, vid: UUID) -> PromptVariant | None:
        stmt = select(PromptVariant).where(PromptVariant.id == vid)
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def get_by_nome(self, nome: str) -> PromptVariant | None:
        stmt = select(PromptVariant).where(PromptVariant.nome == nome)
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def list_all(self) -> list[PromptVariant]:
        stmt = select(PromptVariant).order_by(PromptVariant.nome)
        return list((await self._s.execute(stmt)).scalars().all())

    async def total_trafego_ativo(
        self, canal_slug: str | None = None, exclude_id: UUID | None = None
    ) -> int:
        """Soma trafego_pct das variantes ativas (opcionalmente filtradas por canal).

        ``exclude_id`` ignora uma variante existente no calculo (usado em PATCH).
        """
        stmt = select(func.coalesce(func.sum(PromptVariant.trafego_pct), 0)).where(
            PromptVariant.ativo.is_(True)
        )
        if canal_slug is not None:
            stmt = stmt.where(
                (PromptVariant.canal_slug == canal_slug)
                | (PromptVariant.canal_slug.is_(None))
            )
        if exclude_id is not None:
            stmt = stmt.where(PromptVariant.id != exclude_id)
        return int((await self._s.execute(stmt)).scalar_one())

    async def conversas_por_variante(self) -> dict[str, int]:
        """Conta conversas (nao deletadas) por nome de variante. Util pra metricas."""
        stmt = (
            select(Conversa.prompt_variant, func.count())
            .where(Conversa.deleted_at.is_(None))
            .group_by(Conversa.prompt_variant)
        )
        return {
            (k or "<unset>"): int(v)
            for k, v in (await self._s.execute(stmt)).all()
        }
