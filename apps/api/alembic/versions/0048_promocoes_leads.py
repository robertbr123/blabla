"""Promoções Fase 2: landing de detalhe + leads de interesse.

- `promocoes.descricao_longa` / `promocoes.regulamento` — conteúdo da landing.
- `promocoes_leads` — "Tenho interesse" vira lead com workflow de status
  (novo → contatado → convertido | descartado). Unique (promocao, user).

Revision ID: 0048_promocoes_leads
Revises: 0047_os_sinal
Create Date: 2026-06-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0048_promocoes_leads"
down_revision: str | None = "0047_os_sinal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("promocoes", sa.Column("descricao_longa", sa.Text(), nullable=True))
    op.add_column("promocoes", sa.Column("regulamento", sa.Text(), nullable=True))

    op.create_table(
        "promocoes_leads",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "promocao_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("promocoes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("cliente_app_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contrato_id", sa.String(64), nullable=True),
        sa.Column("nome_snapshot", sa.String(160), nullable=False, server_default=""),
        sa.Column("telefone_snapshot", sa.String(32), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False, server_default="novo"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "promocao_id", "cliente_app_user_id", name="uq_promo_lead_user"
        ),
    )
    op.create_index(
        "ix_promocoes_leads_status", "promocoes_leads", ["status"]
    )


def downgrade() -> None:
    op.drop_index("ix_promocoes_leads_status", table_name="promocoes_leads")
    op.drop_table("promocoes_leads")
    op.drop_column("promocoes", "regulamento")
    op.drop_column("promocoes", "descricao_longa")
