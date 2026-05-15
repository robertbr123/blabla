"""os_pppoe_fields — adicionar pppoe_login e pppoe_senha em ordens_servico.

Revision ID: 0008_os_pppoe_fields
Revises: 0007_os_cliente_nullable
Create Date: 2026-05-14
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_os_pppoe_fields"
down_revision: str | None = "0007_os_cliente_nullable"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ordens_servico", sa.Column("pppoe_login", sa.String(120), nullable=True))
    op.add_column("ordens_servico", sa.Column("pppoe_senha", sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column("ordens_servico", "pppoe_senha")
    op.drop_column("ordens_servico", "pppoe_login")
