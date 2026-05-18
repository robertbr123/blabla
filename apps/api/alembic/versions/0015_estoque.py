"""F6 — Estoque do técnico: itens + movimentos.

Saldo por técnico é computado on-the-fly (sum com sign por tipo) — sem view
materializada. Cargas baixas (poucas centenas de movimentos/dia/técnico)
não justificam complexidade de trigger.

Movimentos têm `tipo` que determina o sinal aplicado ao saldo:
  entrada/ajuste_positivo  → +quantidade
  saida/devolucao/perda/ajuste_negativo → -quantidade

Revision ID: 0015_estoque
Revises: 0014_prompt_variant
Create Date: 2026-05-18
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_estoque"
down_revision: str | None = "0014_prompt_variant"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "estoque_item",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sku", sa.String(40), nullable=False, unique=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("categoria", sa.String(20), nullable=False),
        sa.Column(
            "serializado", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "ativo", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "estoque_movimento",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "item_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("estoque_item.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "tecnico_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tecnicos.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("serial", sa.String(120), nullable=True),
        sa.Column(
            "ordem_servico_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ordens_servico.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column(
            "criado_por",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("quantidade > 0", name="ck_estoque_quantidade_positiva"),
        sa.CheckConstraint(
            "tipo IN ('entrada','saida','devolucao','perda','ajuste_positivo','ajuste_negativo')",
            name="ck_estoque_tipo_enum",
        ),
    )
    op.create_index(
        "ix_estoque_mov_tecnico_item",
        "estoque_movimento",
        ["tecnico_id", "item_id"],
    )
    op.create_index(
        "ix_estoque_mov_os",
        "estoque_movimento",
        ["ordem_servico_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_estoque_mov_os", table_name="estoque_movimento")
    op.drop_index("ix_estoque_mov_tecnico_item", table_name="estoque_movimento")
    op.drop_table("estoque_movimento")
    op.drop_table("estoque_item")
