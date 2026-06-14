"""Comunicados v2: botoes em templates, origem/button_param em campanha,
params por destinatario, cliente_id nullable.

Revision ID: 0050_comunicados_v2
Revises: 0049_comunicados_broadcast
Create Date: 2026-06-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0050_comunicados_v2"
down_revision: str | None = "0049_comunicados_broadcast"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "broadcast_templates",
        sa.Column("botoes", postgresql.JSONB, nullable=False, server_default="[]"),
    )
    op.add_column(
        "campanhas",
        sa.Column("origem", sa.String(12), nullable=False, server_default="segmento"),
    )
    op.add_column("campanhas", sa.Column("button_param", sa.Text(), nullable=True))
    op.add_column(
        "campanha_destinatarios",
        sa.Column("body_params", postgresql.JSONB, nullable=True),
    )
    op.add_column(
        "campanha_destinatarios", sa.Column("button_param", sa.Text(), nullable=True)
    )
    op.alter_column("campanha_destinatarios", "cliente_id", nullable=True)


def downgrade() -> None:
    op.alter_column("campanha_destinatarios", "cliente_id", nullable=False)
    op.drop_column("campanha_destinatarios", "button_param")
    op.drop_column("campanha_destinatarios", "body_params")
    op.drop_column("campanhas", "button_param")
    op.drop_column("campanhas", "origem")
    op.drop_column("broadcast_templates", "botoes")
