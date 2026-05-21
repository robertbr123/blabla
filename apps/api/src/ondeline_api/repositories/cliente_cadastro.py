"""Repo de clientes cadastrados em campo.

Encapsula busca, dedup por cpf_hash, paginacao por cursor (criado_em desc),
filtros (cidade, sgp_status, installer) e soft delete.
"""
from __future__ import annotations

import unicodedata
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import ClienteCadastro


def normalize_nome(nome: str | None) -> str | None:
    """Lowercase + remove acentos para indexação de busca."""
    if not nome:
        return None
    s = nome.strip()
    if not s:
        return None
    # NFD separa caractere base + diacrítico → remove combining marks
    nfd = unicodedata.normalize("NFD", s)
    no_accent = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return no_accent.lower()


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
        cities: list[str] | None = None,  # filtro por áreas do técnico
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
            q_clean = q.strip()
            # Detecta CPF/CNPJ: maioria dígitos com possíveis máscaras.
            digits_only = "".join(c for c in q_clean if c.isdigit())
            cpf_hash_match: str | None = None
            if 11 <= len(digits_only) <= 14 and len(digits_only) == len(
                q_clean.replace(".", "").replace("-", "").replace("/", "").replace(" ", "")
            ):
                # Hashea pra match exato em cpf_hash.
                from ondeline_api.db.crypto import hash_pii

                cpf_hash_match = hash_pii(digits_only)

            q_like = f"%{q_clean}%"
            q_norm = normalize_nome(q_clean)
            conditions = [
                ClienteCadastro.serial.ilike(q_like),
                ClienteCadastro.city.ilike(q_like),
                ClienteCadastro.address.ilike(q_like),
                ClienteCadastro.contrato.ilike(q_like),
            ]
            if q_norm:
                conditions.append(
                    ClienteCadastro.nome_normalized.ilike(f"%{q_norm}%")
                )
            if cpf_hash_match:
                conditions.append(ClienteCadastro.cpf_hash == cpf_hash_match)
            stmt = stmt.where(or_(*conditions))
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
        if cities is not None:
            if not cities:
                # Técnico sem áreas cadastradas → não vê nada (vazio explícito).
                return [], None
            # Case-insensitive match contra a lista de cidades.
            lowered = [c.lower() for c in cities]
            stmt = stmt.where(func.lower(ClienteCadastro.city).in_(lowered))
        if cursor is not None:
            stmt = stmt.where(ClienteCadastro.created_at < cursor)
        stmt = stmt.order_by(desc(ClienteCadastro.created_at)).limit(limit + 1)
        rows = list((await self._s.execute(stmt)).scalars().all())
        next_cursor = None
        if len(rows) > limit:
            next_cursor = rows[limit].created_at
            rows = rows[:limit]
        return rows, next_cursor

    async def count_stats(self, *, cities: list[str] | None = None) -> dict[str, int]:
        """Conta totais agregados: total, synced (com SGP), pending (sem SGP).

        Se `cities` vier, filtra por essas cidades (técnico só conta o que ele vê).
        """
        if cities is not None and not cities:
            return {"total": 0, "synced": 0, "pending": 0}
        synced_expr = func.count().filter(ClienteCadastro.sgp_synced_at.is_not(None))
        pending_expr = func.count().filter(ClienteCadastro.sgp_synced_at.is_(None))
        stmt = select(
            func.count().label("total"),
            synced_expr.label("synced"),
            pending_expr.label("pending"),
        ).where(ClienteCadastro.deleted_at.is_(None))
        if cities is not None:
            lowered = [c.lower() for c in cities]
            stmt = stmt.where(func.lower(ClienteCadastro.city).in_(lowered))
        row = (await self._s.execute(stmt)).one()
        return {"total": int(row.total), "synced": int(row.synced), "pending": int(row.pending)}

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
