"""ORM models de promoções (carrossel da home do app cliente)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ondeline_api.db.base import Base


class Promocao(Base):
    __tablename__ = "promocoes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    titulo: Mapped[str] = mapped_column(String(120), nullable=False)
    subtitulo: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    imagem_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cta_label: Mapped[str] = mapped_column(String(40), nullable=False, default="Saiba mais")
    # Formato: "url:https://..." | "tela:/indicacao" | "info"
    cta_action: Mapped[str] = mapped_column(String(240), nullable=False, default="info")
    # "generica" | "indicacao" (futuros tipos especializados aqui)
    tipo: Mapped[str] = mapped_column(String(24), nullable=False, default="generica")
    ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valido_de: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valido_ate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # "todos" | "inadimplentes" | "adimplentes" | "plano:<id>"
    segmento: Mapped[str] = mapped_column(String(64), nullable=False, default="todos")
    # Cores do gradient do card (hex #RRGGBB ou #RRGGBBAA). Se null usa default por tipo.
    gradient_from: Mapped[str | None] = mapped_column(String(9), nullable=True)
    gradient_to: Mapped[str | None] = mapped_column(String(9), nullable=True)
    # Nome do icone Material (ex: "rocket_launch_rounded"). App mapeia.
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Landing de detalhe no app (Fase 2). Opcionais — promo sem descrição
    # continua funcionando só com subtítulo.
    descricao_longa: Mapped[str | None] = mapped_column(Text, nullable=True)
    regulamento: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class PromocaoEvento(Base):
    __tablename__ = "promocoes_eventos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    promocao_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("promocoes.id", ondelete="CASCADE"),
        nullable=False,
    )
    cliente_app_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)  # view | click | detail_view
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PromocaoLead(Base):
    """Lead de "Tenho interesse" — cliente demonstrou interesse numa promo.

    Snapshot de nome/telefone na hora do clique pra equipe de vendas não
    precisar cruzar com SGP. Unique por (promocao, user): sem lead duplicado.
    """

    __tablename__ = "promocoes_leads"
    __table_args__ = (
        UniqueConstraint(
            "promocao_id", "cliente_app_user_id", name="uq_promo_lead_user"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    promocao_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("promocoes.id", ondelete="CASCADE"),
        nullable=False,
    )
    cliente_app_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    contrato_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nome_snapshot: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    telefone_snapshot: Mapped[str] = mapped_column(
        String(32), nullable=False, default=""
    )
    # novo → contatado → convertido | descartado
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="novo")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
