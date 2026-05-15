"""os: nome_sgp fallback quando cliente_id é nulo.

Revision ID: 0010_os_nome_sgp
Revises: 0009_os_plano_relatorio
Create Date: 2026-05-14
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_os_nome_sgp"
down_revision: str | None = "0009_os_plano_relatorio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ordens_servico", sa.Column("nome_sgp", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ordens_servico", "nome_sgp")
