"""Comunicados v3: snapshot csv_cidade/status/plano no destinatario (base filtravel).

Revision ID: 0051_comunicados_v3
Revises: 0050_comunicados_v2
Create Date: 2026-06-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0051_comunicados_v3"
down_revision: str | None = "0050_comunicados_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("campanha_destinatarios", sa.Column("csv_cidade", sa.String(80), nullable=True))
    op.add_column("campanha_destinatarios", sa.Column("csv_status", sa.String(40), nullable=True))
    op.add_column("campanha_destinatarios", sa.Column("csv_plano", sa.String(80), nullable=True))


def downgrade() -> None:
    op.drop_column("campanha_destinatarios", "csv_plano")
    op.drop_column("campanha_destinatarios", "csv_status")
    op.drop_column("campanha_destinatarios", "csv_cidade")
