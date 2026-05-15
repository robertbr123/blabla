"""os: plano, relatorio, houve_visita, materiais.

Revision ID: 0009_os_plano_relatorio
Revises: 0008_os_pppoe_fields
Create Date: 2026-05-14
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_os_plano_relatorio"
down_revision: str | None = "0008_os_pppoe_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ordens_servico", sa.Column("plano", sa.String(120), nullable=True))
    op.add_column("ordens_servico", sa.Column("relatorio", sa.Text(), nullable=True))
    op.add_column("ordens_servico", sa.Column("houve_visita", sa.Boolean(), nullable=True))
    op.add_column("ordens_servico", sa.Column("materiais", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ordens_servico", "materiais")
    op.drop_column("ordens_servico", "houve_visita")
    op.drop_column("ordens_servico", "relatorio")
    op.drop_column("ordens_servico", "plano")
