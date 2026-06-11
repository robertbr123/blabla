"""ordens_servico: coluna sinal (snapshot optico no momento da OS).

Revision ID: 0047_os_sinal
Revises: 0046_rede_wifi_pedido_tipo
Create Date: 2026-06-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0047_os_sinal"
down_revision: str | None = "0046_rede_wifi_pedido_tipo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ordens_servico",
        sa.Column("sinal", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ordens_servico", "sinal")
