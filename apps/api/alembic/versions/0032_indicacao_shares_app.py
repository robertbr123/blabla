"""Contador shares_app na tabela indicacao.

Conta quantas vezes o cliente tocou "Compartilhar via WhatsApp" na tela
in-app de indicacao. E separado de `usos` (que conta leads concretos
que chegaram pelo bot WhatsApp).

Revision ID: 0032_indicacao_shares_app
Revises: 0031_indicacao_uso_origem
Create Date: 2026-05-22
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032_indicacao_shares_app"
down_revision: str | None = "0031_indicacao_uso_origem"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "indicacao",
        sa.Column(
            "shares_app",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("indicacao", "shares_app")
