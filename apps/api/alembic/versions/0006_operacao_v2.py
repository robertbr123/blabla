"""operacao_v2 — SLA fields e metadata na tabela conversas.

Revision ID: 0006_operacao_v2
Revises: 0005_os_followup_reatribuicao
Create Date: 2026-05-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0006_operacao_v2"
down_revision: str | None = "0005_os_followup_reatribuicao"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversas",
        sa.Column("transferred_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "conversas",
        sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "conversas",
        sa.Column("tags", JSONB, nullable=True),
    )
    op.add_column(
        "conversas",
        sa.Column("sla_minutes", sa.Integer, nullable=False, server_default="15"),
    )
    op.add_column(
        "conversas",
        sa.Column("checklist_metadata", JSONB, nullable=True),
    )
    op.create_index(
        "ix_conversas_transferred_at",
        "conversas",
        ["transferred_at"],
        postgresql_where=sa.text("deleted_at IS NULL AND transferred_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_conversas_transferred_at", table_name="conversas")
    op.drop_column("conversas", "checklist_metadata")
    op.drop_column("conversas", "sla_minutes")
    op.drop_column("conversas", "tags")
    op.drop_column("conversas", "first_response_at")
    op.drop_column("conversas", "transferred_at")
