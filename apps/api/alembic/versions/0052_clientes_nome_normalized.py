"""Add nome_normalized column to clientes for conversa name search.

Revision ID: 0052_clientes_nome_normalized
Revises: 0051_comunicados_v3
Create Date: 2026-07-02
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0052_clientes_nome_normalized"
down_revision: str | None = "0051_comunicados_v3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Idempotente — caso a coluna já exista em deploy parcial.
    op.execute(
        "ALTER TABLE clientes "
        "ADD COLUMN IF NOT EXISTS nome_normalized VARCHAR(255)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_clientes_nome_norm "
        "ON clientes (nome_normalized)"
    )
    # Backfill dos registros existentes: scripts/backfill_clientes_nome_normalized.py
    # (decifra nome_encrypted). Novos/atualizados já entram preenchidos via
    # ClienteRepo.upsert_from_sgp.


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_clientes_nome_norm")
    op.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS nome_normalized")
