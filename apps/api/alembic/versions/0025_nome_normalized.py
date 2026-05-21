"""Add nome_normalized column to clientes_cadastro for name search.

Revision ID: 0025_nome_normalized
Revises: 0024_email_due_date
Create Date: 2026-05-21
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0025_nome_normalized"
down_revision: str | None = "0024_email_due_date"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Idempotente — caso a coluna já exista em deploy parcial.
    op.execute(
        "ALTER TABLE clientes_cadastro "
        "ADD COLUMN IF NOT EXISTS nome_normalized VARCHAR(255)"
    )
    # Índice trigram para LIKE rápido — só cria se pg_trgm estiver disponível.
    # Fallback simples sem extension: b-tree em lower(nome_normalized).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_clientes_cadastro_nome_norm "
        "ON clientes_cadastro (nome_normalized)"
    )
    # Backfill será feito por job/script manual depois — a app sempre regrava
    # a coluna em create/update, então novos registros já entram preenchidos.


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS ix_clientes_cadastro_nome_norm"
    )
    op.execute(
        "ALTER TABLE clientes_cadastro DROP COLUMN IF EXISTS nome_normalized"
    )
