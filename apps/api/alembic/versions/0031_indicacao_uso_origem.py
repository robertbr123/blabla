"""Coluna `origem` em indicacao_uso (app | whatsapp).

Distingue indicações registradas pelo app cliente (compartilhamento via tela
in-app) das vindas pelo bot WhatsApp tradicional. Existentes assumem
`whatsapp` (default).

Revision ID: 0031_indicacao_uso_origem
Revises: 0030_promocoes
Create Date: 2026-05-22
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_indicacao_uso_origem"
down_revision: str | None = "0030_promocoes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "indicacao_uso",
        sa.Column(
            "origem",
            sa.String(16),
            nullable=False,
            server_default="whatsapp",
        ),
    )
    op.create_index(
        "ix_indicacao_uso_origem",
        "indicacao_uso",
        ["origem"],
    )


def downgrade() -> None:
    op.drop_index("ix_indicacao_uso_origem", table_name="indicacao_uso")
    op.drop_column("indicacao_uso", "origem")
