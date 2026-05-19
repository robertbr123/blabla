"""Repo de estoque (F6)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.estoque import (
    TIPOS_POSITIVOS,
    EstoqueItem,
    EstoqueMovimento,
)


class ItemRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_id(self, item_id: UUID) -> EstoqueItem | None:
        return (
            await self._s.execute(select(EstoqueItem).where(EstoqueItem.id == item_id))
        ).scalar_one_or_none()

    async def get_by_sku(self, sku: str) -> EstoqueItem | None:
        return (
            await self._s.execute(select(EstoqueItem).where(EstoqueItem.sku == sku))
        ).scalar_one_or_none()

    async def list_all(self, *, ativos_only: bool = False) -> list[EstoqueItem]:
        stmt = select(EstoqueItem)
        if ativos_only:
            stmt = stmt.where(EstoqueItem.ativo.is_(True))
        stmt = stmt.order_by(EstoqueItem.nome)
        return list((await self._s.execute(stmt)).scalars().all())


class MovimentoRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def insert(self, mov: EstoqueMovimento) -> EstoqueMovimento:
        self._s.add(mov)
        await self._s.flush()
        return mov

    async def list_by_tecnico(
        self,
        tecnico_id: UUID | None,
        *,
        item_id: UUID | None = None,
        ordem_servico_id: UUID | None = None,
        limit: int = 100,
    ) -> list[EstoqueMovimento]:
        stmt = select(EstoqueMovimento)
        if tecnico_id is None:
            stmt = stmt.where(EstoqueMovimento.tecnico_id.is_(None))
        else:
            stmt = stmt.where(EstoqueMovimento.tecnico_id == tecnico_id)
        if item_id is not None:
            stmt = stmt.where(EstoqueMovimento.item_id == item_id)
        if ordem_servico_id is not None:
            stmt = stmt.where(EstoqueMovimento.ordem_servico_id == ordem_servico_id)
        stmt = stmt.order_by(EstoqueMovimento.criado_em.desc()).limit(limit)
        return list((await self._s.execute(stmt)).scalars().all())

    async def saldo_por_tecnico_item(
        self, tecnico_id: UUID, item_id: UUID
    ) -> int:
        """Saldo agregado: +qty para tipos positivos, -qty pros negativos."""
        sign = case(
            (EstoqueMovimento.tipo.in_(list(TIPOS_POSITIVOS)), EstoqueMovimento.quantidade),
            else_=-EstoqueMovimento.quantidade,
        )
        stmt = (
            select(func.coalesce(func.sum(sign), 0))
            .where(
                EstoqueMovimento.tecnico_id == tecnico_id,
                EstoqueMovimento.item_id == item_id,
            )
        )
        return int((await self._s.execute(stmt)).scalar_one())

    async def saldo_full_por_tecnico(
        self, tecnico_id: UUID
    ) -> list[tuple[EstoqueItem, int]]:
        """Saldo de todos os itens pra um técnico. Retorna lista de (item, saldo).

        Itens com saldo zero ou negativo entram na lista — ajuda o admin a
        detectar movimentos quebrados.
        """
        sign = case(
            (EstoqueMovimento.tipo.in_(list(TIPOS_POSITIVOS)), EstoqueMovimento.quantidade),
            else_=-EstoqueMovimento.quantidade,
        )
        stmt = (
            select(EstoqueItem, func.coalesce(func.sum(sign), 0).label("saldo"))
            .outerjoin(
                EstoqueMovimento,
                (EstoqueMovimento.item_id == EstoqueItem.id)
                & (EstoqueMovimento.tecnico_id == tecnico_id),
            )
            .where(EstoqueItem.ativo.is_(True))
            .group_by(EstoqueItem.id)
            .order_by(EstoqueItem.nome)
        )
        return [(item, int(saldo)) for item, saldo in (await self._s.execute(stmt)).all()]

    async def ultimo_movimento_serial(
        self, item_id: UUID, serial: str
    ) -> EstoqueMovimento | None:
        """Devolve o ultimo movimento envolvendo esse serial (item+serial unico)."""
        stmt = (
            select(EstoqueMovimento)
            .where(
                EstoqueMovimento.item_id == item_id,
                EstoqueMovimento.serial == serial,
            )
            .order_by(EstoqueMovimento.criado_em.desc())
            .limit(1)
        )
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def saldo_do_serial(self, item_id: UUID, serial: str) -> int:
        """Soma com sinal (+1 pra positivos, -1 pra negativos) dos movimentos
        desse serial. Saldo > 0 = serial atualmente em estoque (por qualquer tecnico).

        Imune a problemas de timestamp identico — eh aritmetica pura sobre tipo.
        """
        sign = case(
            (
                EstoqueMovimento.tipo.in_(list(TIPOS_POSITIVOS)),
                EstoqueMovimento.quantidade,
            ),
            else_=-EstoqueMovimento.quantidade,
        )
        stmt = (
            select(func.coalesce(func.sum(sign), 0))
            .where(
                EstoqueMovimento.item_id == item_id,
                EstoqueMovimento.serial == serial,
            )
        )
        return int((await self._s.execute(stmt)).scalar_one())

    async def list_recentes_por_os(
        self, os_id: UUID
    ) -> list[EstoqueMovimento]:
        stmt = (
            select(EstoqueMovimento)
            .where(EstoqueMovimento.ordem_servico_id == os_id)
            .order_by(EstoqueMovimento.criado_em.desc())
        )
        return list((await self._s.execute(stmt)).scalars().all())

    async def list_recentes_global(
        self,
        *,
        since: datetime | None = None,
        limit: int = 200,
    ) -> list[EstoqueMovimento]:
        stmt = select(EstoqueMovimento)
        if since is not None:
            stmt = stmt.where(EstoqueMovimento.criado_em >= since)
        stmt = stmt.order_by(EstoqueMovimento.criado_em.desc()).limit(limit)
        return list((await self._s.execute(stmt)).scalars().all())
