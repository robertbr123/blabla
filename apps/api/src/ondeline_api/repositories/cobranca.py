"""Repo de cobranca_lembrete (F2)."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import Date, cast, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import CobrancaLembrete


class CobrancaRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def ja_enviado(
        self, cliente_id: UUID, fatura_id: str, gatilho: str
    ) -> bool:
        stmt = select(CobrancaLembrete.id).where(
            CobrancaLembrete.cliente_id == cliente_id,
            CobrancaLembrete.fatura_id == fatura_id,
            CobrancaLembrete.gatilho == gatilho,
        )
        return (await self._s.execute(stmt)).scalar_one_or_none() is not None

    async def registrar(
        self,
        *,
        cliente_id: UUID,
        fatura_id: str,
        gatilho: str,
        vencimento: date,
    ) -> CobrancaLembrete | None:
        """Insere lembrete; devolve `None` se ja existia (idempotente via UNIQUE).

        Usa ``ON CONFLICT DO NOTHING`` pra evitar race condition entre
        verificacao e insercao quando dois workers rodarem o mesmo cliente.
        """
        stmt = (
            pg_insert(CobrancaLembrete)
            .values(
                cliente_id=cliente_id,
                fatura_id=fatura_id,
                gatilho=gatilho,
                vencimento=vencimento,
            )
            .on_conflict_do_nothing(
                index_elements=["cliente_id", "fatura_id", "gatilho"]
            )
            .returning(CobrancaLembrete)
        )
        row = (await self._s.execute(stmt)).scalar_one_or_none()
        return row

    async def enviados_hoje_por_cliente(
        self, cliente_id: UUID, today: date
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(CobrancaLembrete)
            .where(
                CobrancaLembrete.cliente_id == cliente_id,
                cast(CobrancaLembrete.enviado_em, Date) == today,
            )
        )
        return int((await self._s.execute(stmt)).scalar_one())
