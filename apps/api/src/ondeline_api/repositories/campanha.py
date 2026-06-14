# apps/api/src/ondeline_api/repositories/campanha.py
"""CampanhaRepo — CRUD de campanhas + agregação de status dos destinatários."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, true, update
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Campanha, CampanhaDestinatario


class CampanhaRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Campanha]:
        stmt = select(Campanha).order_by(Campanha.created_at.desc())
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_by_id(self, campanha_id: UUID) -> Campanha | None:
        stmt = select(Campanha).where(Campanha.id == campanha_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def status_counts(self, campanha_id: UUID) -> dict[str, int]:
        """Conta destinatários por status (pendente/enviada/entregue/lida/falha)."""
        stmt = (
            select(CampanhaDestinatario.status, func.count())
            .where(CampanhaDestinatario.campanha_id == campanha_id)
            .group_by(CampanhaDestinatario.status)
        )
        rows = (await self._session.execute(stmt)).all()
        return {str(status): int(n) for status, n in rows}

    @staticmethod
    def _match_csv(filtros: dict[str, Any]) -> Any:
        conds = []
        if (filtros.get("cidade") or "").strip():
            conds.append(CampanhaDestinatario.csv_cidade == filtros["cidade"])
        if (filtros.get("status") or "").strip():
            conds.append(CampanhaDestinatario.csv_status == filtros["status"])
        if (filtros.get("plano") or "").strip():
            conds.append(CampanhaDestinatario.csv_plano == filtros["plano"])
        return and_(*conds) if conds else true()

    async def contar_selecionados(self, campanha_id: UUID, filtros: dict[str, Any]) -> int:
        stmt = (
            select(func.count())
            .select_from(CampanhaDestinatario)
            .where(
                CampanhaDestinatario.campanha_id == campanha_id,
                CampanhaDestinatario.status == "pendente",
                self._match_csv(filtros),
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def marcar_excluidos(self, campanha_id: UUID, filtros: dict[str, Any]) -> int:
        stmt = (
            update(CampanhaDestinatario)
            .where(
                CampanhaDestinatario.campanha_id == campanha_id,
                CampanhaDestinatario.status == "pendente",
                ~self._match_csv(filtros),
            )
            .values(status="excluido")
        )
        await self._session.execute(stmt)
        return await self.contar_selecionados(campanha_id, filtros)

    async def valores_import(self, campanha_id: UUID) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for chave, coluna in (
            ("cidades", CampanhaDestinatario.csv_cidade),
            ("status", CampanhaDestinatario.csv_status),
            ("planos", CampanhaDestinatario.csv_plano),
        ):
            stmt = (
                select(coluna)
                .where(
                    CampanhaDestinatario.campanha_id == campanha_id,
                    coluna.is_not(None),
                    coluna != "",
                )
                .distinct()
                .order_by(coluna)
            )
            out[chave] = [v for (v,) in (await self._session.execute(stmt)).all() if v is not None]
        return out

    async def list_destinatarios(
        self, campanha_id: UUID, *, status: str | None, limit: int, offset: int
    ) -> list[CampanhaDestinatario]:
        stmt = select(CampanhaDestinatario).where(
            CampanhaDestinatario.campanha_id == campanha_id
        )
        if status:
            stmt = stmt.where(CampanhaDestinatario.status == status)
        else:
            stmt = stmt.where(CampanhaDestinatario.status != "excluido")
        stmt = stmt.order_by(CampanhaDestinatario.id).limit(limit).offset(offset)
        return list((await self._session.execute(stmt)).scalars().all())

    async def reenviar_falhas(self, campanha_id: UUID) -> int:
        falhas = list(
            (
                await self._session.execute(
                    select(CampanhaDestinatario).where(
                        CampanhaDestinatario.campanha_id == campanha_id,
                        CampanhaDestinatario.status == "falha",
                    )
                )
            )
            .scalars()
            .all()
        )
        for d in falhas:
            d.status = "pendente"
            d.erro = None
            d.wamid = None
        return len(falhas)
