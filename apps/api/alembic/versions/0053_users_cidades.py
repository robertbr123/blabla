"""Add cidades (JSONB) to users — escopo de cidades do atendente.

Revision ID: 0053_users_cidades
Revises: 0052_clientes_nome_normalized
Create Date: 2026-10-09
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0053_users_cidades"
down_revision: str | None = "0052_clientes_nome_normalized"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NULL / [] = sem restricao (comportamento de todos os usuarios existentes).
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS cidades JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS cidades")
