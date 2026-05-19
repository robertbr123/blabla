"""Repo de clientes cadastrados em campo.

Encapsula busca, dedup por cpf_hash, paginacao por cursor (criado_em desc),
filtros (cidade, sgp_status, installer) e soft delete.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import ClienteCadastro


class ClienteCadastroRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_id(self, cliente_id: UUID) -> ClienteCadastro | None:
        stmt = select(ClienteCadastro).where(
            ClienteCadastro.id == cliente_id,
            ClienteCadastro.deleted_at.is_(None),
        )
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def get_by_cpf_hash(self, cpf_hash: str) -> ClienteCadastro | None:
        stmt = select(ClienteCadastro).where(
            ClienteCadastro.cpf_hash == cpf_hash,
            ClienteCadastro.deleted_at.is_(None),
        )
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def list_paginated(
        self,
        *,
        q: str | None = None,
        city: str | None = None,
        sgp_status: str | None = None,   # synced | pending | None
        installer_user_id: UUID | None = None,
        cursor: datetime | None = None,
        limit: int = 50,
    ) -> tuple[list[ClienteCadastro], datetime | None]:
        """Lista paginada por cursor (created_at desc).

        - `q` casa contra serial OU city (em plain). CPF/nome ficam encriptados
          e nao sao searchable por texto — usar `get_by_cpf_hash` pra CPF.
        - `sgp_status`: 'synced' (sgp_synced_at NOT NULL) ou 'pending' (IS NULL)
        """
        stmt = select(ClienteCadastro).where(ClienteCadastro.deleted_at.is_(None))
        if q:
            q_like = f"%{q}%"
            stmt = stmt.where(
                or_(
                    ClienteCadastro.serial.ilike(q_like),
                    ClienteCadastro.city.ilike(q_like),
                    ClienteCadastro.address.ilike(q_like),
                    ClienteCadastro.contrato.ilike(q_like),
                )
            )
        if city:
            stmt = stmt.where(ClienteCadastro.city.ilike(city))
        if sgp_status == "synced":
            stmt = stmt.where(ClienteCadastro.sgp_synced_at.is_not(None))
        elif sgp_status == "pending":
            stmt = stmt.where(ClienteCadastro.sgp_synced_at.is_(None))
        if installer_user_id is not None:
            stmt = stmt.where(
                ClienteCadastro.installer_user_id == installer_user_id
            )
        if cursor is not None:
            stmt = stmt.where(ClienteCadastro.created_at < cursor)
        stmt = stmt.order_by(desc(ClienteCadastro.created_at)).limit(limit + 1)
        rows = list((await self._s.execute(stmt)).scalars().all())
        next_cursor = None
        if len(rows) > limit:
            next_cursor = rows[limit].created_at
            rows = rows[:limit]
        return rows, next_cursor

    async def create(self, cliente: ClienteCadastro) -> ClienteCadastro:
        self._s.add(cliente)
        await self._s.flush()
        return cliente

    async def soft_delete(self, cliente: ClienteCadastro) -> None:
        cliente.deleted_at = datetime.now(tz=None)
        await self._s.flush()

    async def add_foto(
        self, cliente: ClienteCadastro, foto: dict[str, Any]
    ) -> None:
        """Acrescenta uma foto na lista (JSONB). Pra setar JSONB modificado o
        SQLAlchemy precisa do reassign, nao basta mutar in-place.
        """
        atual = list(cliente.fotos or [])
        atual.append(foto)
        cliente.fotos = atual
        await self._s.flush()

    async def remove_foto(
        self, cliente: ClienteCadastro, foto_idx: int
    ) -> dict[str, Any] | None:
        """Remove e retorna o dict removido (pra apagar arquivo). None se idx invalido."""
        atual = list(cliente.fotos or [])
        if foto_idx < 0 or foto_idx >= len(atual):
            return None
        removed = atual.pop(foto_idx)
        cliente.fotos = atual or None
        await self._s.flush()
        return removed

    async def marcar_sincronizado(
        self, cliente: ClienteCadastro, sgp_id: str
    ) -> None:
        from datetime import UTC

        cliente.sgp_id = sgp_id
        cliente.sgp_synced_at = datetime.now(tz=UTC)
        await self._s.flush()
