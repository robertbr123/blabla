"""F10 — Indicação 'Indicou, ganhou'.

Tabela `indicacao` (códigos únicos gerados por clientes ativos).
Tabela `indicacao_uso` (cada vez que o link foi usado por alguém).
`leads.indicacao_id` opcional (lead veio por indicação).

Revision ID: 0019_indicacao
Revises: 0018_cliente_equipamento
Create Date: 2026-05-18
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_indicacao"
down_revision: str | None = "0018_cliente_equipamento"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "indicacao",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("codigo", sa.String(16), nullable=False, unique=True),
        sa.Column(
            "cliente_indicador_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "expira_em",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("usos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "ativo", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.create_index(
        "ix_indicacao_cliente", "indicacao", ["cliente_indicador_id"]
    )

    op.create_table(
        "indicacao_uso",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "indicacao_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("indicacao.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lead_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "cliente_indicado_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "convertido_em",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "credito_aplicado_em",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("observacao", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_indicacao_uso_indicacao", "indicacao_uso", ["indicacao_id"]
    )

    op.add_column(
        "leads",
        sa.Column(
            "indicacao_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("indicacao.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("leads", "indicacao_id")
    op.drop_index("ix_indicacao_uso_indicacao", table_name="indicacao_uso")
    op.drop_table("indicacao_uso")
    op.drop_index("ix_indicacao_cliente", table_name="indicacao")
    op.drop_table("indicacao")
