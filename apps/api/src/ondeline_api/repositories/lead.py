"""LeadRepo — CRUD + filtered pagination."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Lead, LeadStatus

# Leads "abertos" — ainda em andamento. convertido/perdido sao terminais:
# se a pessoa voltar depois de fechado, abre-se um lead novo.
_OPEN_STATUSES = (LeadStatus.NOVO, LeadStatus.CONTATO)

# Prefixo do nome-placeholder gerado quando nao temos o nome real (ex.:
# lead criado na transferencia pra humano). Serve pra saber que o nome pode
# ser "promovido" pra o nome real quando o bot finalmente o coletar.
_NOME_PLACEHOLDER_PREFIX = "Contato "


class LeadRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_by_whatsapp(
        self,
        *,
        whatsapp: str,
        nome: str,
        interesse: str | None = None,
        indicacao_id: UUID | None = None,
    ) -> tuple[Lead, bool]:
        """Registra um lead pro ``whatsapp`` de forma idempotente.

        Se ja existe um lead ABERTO (novo/contato) pra esse numero, reusa —
        preenchendo lacunas (interesse vazio) e promovendo o nome-placeholder
        pro nome real — em vez de duplicar. Caso contrario, cria um novo.

        Todos os caminhos de captura (indicacao F10, tool ``registrar_lead``,
        transferencia pra humano) passam por aqui pra nunca gerar 2 leads do
        mesmo contato. Retorna ``(lead, created)``.
        """
        stmt = (
            select(Lead)
            .where(Lead.whatsapp == whatsapp, Lead.status.in_(_OPEN_STATUSES))
            .order_by(desc(Lead.created_at))
            .limit(1)
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            if interesse and not existing.interesse:
                existing.interesse = interesse
            # So sobrescreve o nome se o atual for placeholder (nao rebaixa nome real).
            if nome and existing.nome.startswith(_NOME_PLACEHOLDER_PREFIX):
                existing.nome = nome
            if indicacao_id and existing.indicacao_id is None:
                existing.indicacao_id = indicacao_id
            await self._session.flush()
            return existing, False

        lead = Lead(
            nome=nome,
            whatsapp=whatsapp,
            interesse=interesse,
            status=LeadStatus.NOVO,
            indicacao_id=indicacao_id,
        )
        self._session.add(lead)
        await self._session.flush()
        return lead, True

    async def get_by_id(self, lead_id: UUID) -> Lead | None:
        stmt = select(Lead).where(Lead.id == lead_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_paginated(
        self,
        *,
        status: str | None = None,
        q: str | None = None,
        cursor: datetime | None = None,
        limit: int = 50,
    ) -> tuple[list[Lead], datetime | None]:
        stmt = select(Lead)
        if status:
            stmt = stmt.where(Lead.status == LeadStatus(status))
        if q:
            stmt = stmt.where(Lead.nome.ilike(f"%{q}%"))
        if cursor is not None:
            stmt = stmt.where(Lead.created_at < cursor)
        stmt = stmt.order_by(desc(Lead.created_at)).limit(limit + 1)
        rows = list((await self._session.execute(stmt)).scalars().all())
        if len(rows) > limit:
            # cursor = último item RETORNADO (não o espiado); com `< cursor`
            # estrito, a próxima página não pula o item da fronteira.
            rows = rows[:limit]
            next_cursor = rows[-1].created_at
        else:
            next_cursor = None
        return rows, next_cursor

    async def create(
        self,
        *,
        nome: str,
        whatsapp: str,
        interesse: str | None = None,
        atendente_id: UUID | None = None,
        notas: str | None = None,
    ) -> Lead:
        lead = Lead(
            nome=nome,
            whatsapp=whatsapp,
            interesse=interesse,
            status=LeadStatus.NOVO,
            atendente_id=atendente_id,
            notas=notas,
        )
        self._session.add(lead)
        await self._session.flush()
        return lead

    async def update(
        self,
        lead: Lead,
        *,
        nome: str | None = None,
        interesse: str | None = None,
        status: str | None = None,
        atendente_id: UUID | None = None,
        notas: str | None = None,
    ) -> None:
        if nome is not None:
            lead.nome = nome
        if interesse is not None:
            lead.interesse = interesse
        if status is not None:
            lead.status = LeadStatus(status)
        if atendente_id is not None:
            lead.atendente_id = atendente_id
        if notas is not None:
            lead.notas = notas
        await self._session.flush()
        await self._session.refresh(lead)

    async def delete(self, lead: Lead) -> None:
        await self._session.delete(lead)
        await self._session.flush()
