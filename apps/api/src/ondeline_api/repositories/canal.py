"""Repo de Canal (F4)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Canal


class CanalRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_id(self, canal_id: UUID) -> Canal | None:
        stmt = select(Canal).where(Canal.id == canal_id)
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def get_by_evolution_instance(self, instance: str) -> Canal | None:
        stmt = select(Canal).where(Canal.evolution_instance == instance)
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def get_by_cloud_phone_id(self, phone_id: str) -> Canal | None:
        """Lookup por phone_number_id da Cloud API (Meta).

        Usado pelo webhook /webhook/whatsapp-cloud pra rotear o evento
        ao canal certo (PR3).
        """
        stmt = select(Canal).where(Canal.cloud_phone_id == phone_id)
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Canal | None:
        stmt = select(Canal).where(Canal.slug == slug)
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def list_ativos(self) -> list[Canal]:
        stmt = select(Canal).where(Canal.ativo.is_(True)).order_by(Canal.slug)
        return list((await self._s.execute(stmt)).scalars().all())

    async def list_all(self) -> list[Canal]:
        stmt = select(Canal).order_by(Canal.slug)
        return list((await self._s.execute(stmt)).scalars().all())

    async def ensure_default(
        self,
        *,
        slug: str,
        nome: str,
        evolution_instance: str,
    ) -> Canal:
        """Garante que existe um canal pelo slug. Cria se faltar.

        Chamado no startup do app (lifespan) para inicializar o canal default
        a partir de settings.evolution_instance.
        """
        existing = await self.get_by_slug(slug)
        if existing is not None:
            return existing
        # tenta tambem por evolution_instance (caso slug seja diferente mas instance ja exista)
        existing_inst = await self.get_by_evolution_instance(evolution_instance)
        if existing_inst is not None:
            return existing_inst
        canal = Canal(slug=slug, nome=nome, evolution_instance=evolution_instance)
        self._s.add(canal)
        await self._s.flush()
        return canal
