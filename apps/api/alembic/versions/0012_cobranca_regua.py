"""F2 — Régua de cobranca: tabela cobranca_lembrete + opt-out em clientes.

Revision ID: 0012_cobranca_regua
Revises: 0011_conversa_resumo_handoff
Create Date: 2026-05-18
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_cobranca_regua"
down_revision: str | None = "0011_conversa_resumo_handoff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "clientes",
        sa.Column(
            "cobranca_optout",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "clientes",
        sa.Column("cobranca_optout_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "cobranca_lembrete",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cliente_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fatura_id", sa.String(80), nullable=False),
        sa.Column("gatilho", sa.String(8), nullable=False),  # 'D-3', 'D+1', 'D+5', 'D+15'
        sa.Column("vencimento", sa.Date(), nullable=False),
        sa.Column(
            "enviado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "cliente_id", "fatura_id", "gatilho", name="uq_cobranca_lembrete"
        ),
    )
    op.create_index(
        "ix_cobranca_lembrete_cliente",
        "cobranca_lembrete",
        ["cliente_id", "enviado_em"],
    )


def downgrade() -> None:
    op.drop_index("ix_cobranca_lembrete_cliente", table_name="cobranca_lembrete")
    op.drop_table("cobranca_lembrete")
    op.drop_column("clientes", "cobranca_optout_at")
    op.drop_column("clientes", "cobranca_optout")
