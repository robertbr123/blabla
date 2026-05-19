"""F-OS — Reabertura de OS.

Adiciona suporte para reabrir OS concluida/cancelada:
- reaberta_em: ultima vez que foi reaberta
- reaberta_por: user que reabriu
- reabertura_motivo: justificativa textual
- historico_reaberturas: JSONB acumulando todas as reaberturas

Revision ID: 0020_os_reabertura
Revises: 0019_indicacao
Create Date: 2026-05-19
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_os_reabertura"
down_revision: str | None = "0019_indicacao"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ordens_servico",
        sa.Column("reaberta_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ordens_servico",
        sa.Column("reaberta_por", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "ordens_servico",
        sa.Column("reabertura_motivo", sa.Text(), nullable=True),
    )
    op.add_column(
        "ordens_servico",
        sa.Column("historico_reaberturas", postgresql.JSONB(), nullable=True),
    )
    op.create_foreign_key(
        "fk_ordens_servico_reaberta_por_users",
        "ordens_servico",
        "users",
        ["reaberta_por"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_ordens_servico_reaberta_por_users", "ordens_servico", type_="foreignkey"
    )
    op.drop_column("ordens_servico", "historico_reaberturas")
    op.drop_column("ordens_servico", "reabertura_motivo")
    op.drop_column("ordens_servico", "reaberta_por")
    op.drop_column("ordens_servico", "reaberta_em")
