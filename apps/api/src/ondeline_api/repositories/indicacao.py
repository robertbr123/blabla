"""Repo de Indicação (F10)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import (
    Cliente,
    Indicacao,
    IndicacaoUso,
)


class IndicacaoRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_codigo(self, codigo: str) -> Indicacao | None:
        stmt = select(Indicacao).where(
            Indicacao.codigo == codigo.upper(),
            Indicacao.ativo.is_(True),
        )
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, indicacao_id: UUID) -> Indicacao | None:
        return (
            await self._s.execute(
                select(Indicacao).where(Indicacao.id == indicacao_id)
            )
        ).scalar_one_or_none()

    async def list_por_cliente(self, cliente_id: UUID) -> list[Indicacao]:
        stmt = (
            select(Indicacao)
            .where(Indicacao.cliente_indicador_id == cliente_id)
            .order_by(desc(Indicacao.criado_em))
        )
        return list((await self._s.execute(stmt)).scalars().all())

    async def get_or_create_para_cliente(self, cliente_id: UUID) -> Indicacao:
        """Retorna a indicação ativa do cliente, criando uma se faltar.

        Cada cliente tem 1 indicação ativa por vez — suficiente pra divulgar.
        """
        stmt = (
            select(Indicacao)
            .where(
                Indicacao.cliente_indicador_id == cliente_id,
                Indicacao.ativo.is_(True),
            )
            .order_by(desc(Indicacao.criado_em))
            .limit(1)
        )
        existing = (await self._s.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return existing
        novo = Indicacao(
            cliente_indicador_id=cliente_id,
            codigo=await self._gerar_codigo_unico(),
        )
        self._s.add(novo)
        await self._s.flush()
        return novo

    async def _gerar_codigo_unico(self) -> str:
        """Gera código de 6 chars alfanuméricos (sem 0/O/1/I) único."""
        import secrets

        alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        for _ in range(20):
            cand = "".join(secrets.choice(alfabeto) for _ in range(6))
            if (
                await self._s.execute(
                    select(Indicacao.id).where(Indicacao.codigo == cand)
                )
            ).scalar_one_or_none() is None:
                return cand
        # fallback raro
        return "IND" + "".join(secrets.choice(alfabeto) for _ in range(5))

    async def registrar_uso(
        self,
        indicacao_id: UUID,
        *,
        lead_id: UUID | None = None,
        cliente_indicado_id: UUID | None = None,
    ) -> IndicacaoUso:
        uso = IndicacaoUso(
            indicacao_id=indicacao_id,
            lead_id=lead_id,
            cliente_indicado_id=cliente_indicado_id,
        )
        self._s.add(uso)
        # Incrementa contador.
        await self._s.execute(
            Indicacao.__table__.update()  # type: ignore[attr-defined]
            .where(Indicacao.id == indicacao_id)
            .values(usos=Indicacao.usos + 1)
        )
        await self._s.flush()
        return uso

    async def list_usos(self, indicacao_id: UUID) -> list[IndicacaoUso]:
        stmt = (
            select(IndicacaoUso)
            .where(IndicacaoUso.indicacao_id == indicacao_id)
            .order_by(desc(IndicacaoUso.criado_em))
        )
        return list((await self._s.execute(stmt)).scalars().all())

    async def ranking_indicadores(
        self, limit: int = 20
    ) -> list[tuple[Cliente, int, int]]:
        """Top indicadores: (cliente, qtd_indicacoes_usadas, qtd_convertidas).

        Usa o cliente como chave; soma os usos das indicações dele.
        """
        stmt = (
            select(
                Cliente,
                func.count(IndicacaoUso.id).label("usos"),
                func.sum(
                    case((IndicacaoUso.convertido_em.isnot(None), 1), else_=0)
                ).label("convertidos"),
            )
            .select_from(Cliente)
            .join(Indicacao, Indicacao.cliente_indicador_id == Cliente.id)
            .outerjoin(IndicacaoUso, IndicacaoUso.indicacao_id == Indicacao.id)
            .group_by(Cliente.id)
            .order_by(desc(func.count(IndicacaoUso.id)))
            .limit(limit)
        )
        rows = (await self._s.execute(stmt)).all()
        return [(c, int(usos or 0), int(conv or 0)) for c, usos, conv in rows]
