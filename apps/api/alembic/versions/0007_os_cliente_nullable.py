"""os_cliente_nullable — cliente_id em ordens_servico passa a ser opcional.

Revision ID: 0007_os_cliente_nullable
Revises: 0006_operacao_v2
Create Date: 2026-05-14
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_os_cliente_nullable"
down_revision: str | None = "0006_operacao_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ordens_servico_cliente_id_fkey", "ordens_servico", type_="foreignkey")
    op.alter_column("ordens_servico", "cliente_id", existing_type=sa.dialects.postgresql.UUID(as_uuid=True), nullable=True)
    op.create_foreign_key(
        "ordens_servico_cliente_id_fkey",
        "ordens_servico", "clientes",
        ["cliente_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ordens_servico_cliente_id_fkey", "ordens_servico", type_="foreignkey")
    op.alter_column("ordens_servico", "cliente_id", existing_type=sa.dialects.postgresql.UUID(as_uuid=True), nullable=False)
    op.create_foreign_key(
        "ordens_servico_cliente_id_fkey",
        "ordens_servico", "clientes",
        ["cliente_id"], ["id"],
        ondelete="RESTRICT",
    )
