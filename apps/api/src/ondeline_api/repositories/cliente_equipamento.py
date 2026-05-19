"""Repo de ClienteEquipamento (F8)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.estoque import ClienteEquipamento


class ClienteEquipamentoRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list_by_cliente(
        self, cliente_id: UUID, *, ativos_only: bool = False
    ) -> list[ClienteEquipamento]:
        stmt = select(ClienteEquipamento).where(
            ClienteEquipamento.cliente_id == cliente_id
        )
        if ativos_only:
            stmt = stmt.where(ClienteEquipamento.removido_em.is_(None))
        stmt = stmt.order_by(desc(ClienteEquipamento.instalado_em))
        return list((await self._s.execute(stmt)).scalars().all())

    async def find_ativo_por_serial(
        self, item_id: UUID, serial: str
    ) -> ClienteEquipamento | None:
        """Acha o equipamento ATIVO (não removido) com esse item+serial.

        Útil pra fechar quando técnico faz `recolhido`.
        """
        stmt = (
            select(ClienteEquipamento)
            .where(
                ClienteEquipamento.item_id == item_id,
                ClienteEquipamento.serial == serial,
                ClienteEquipamento.removido_em.is_(None),
            )
            .limit(1)
        )
        return (await self._s.execute(stmt)).scalar_one_or_none()
