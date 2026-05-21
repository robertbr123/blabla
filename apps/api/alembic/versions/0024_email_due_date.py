"""Add optional email to clientes_cadastro and restrict due_date to 10/20/30.

Revision ID: 0024_email_due_date
Revises: 0023_clientes_cadastro
Create Date: 2026-05-20
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0024_email_due_date"
down_revision: str | None = "0023_clientes_cadastro"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Idempotente: prod pode ter aplicado essas mudanças parcialmente
    # quando a versão anterior do nome (37 chars) explodiu no UPDATE
    # de alembic_version (varchar(32)).
    # Alarga a coluna de versão pra evitar reincidir esse bug.
    op.execute(
        "ALTER TABLE alembic_version "
        "ALTER COLUMN version_num TYPE VARCHAR(64)"
    )
    op.execute(
        "ALTER TABLE clientes_cadastro "
        "ADD COLUMN IF NOT EXISTS email_encrypted TEXT"
    )
    op.execute(
        """
        UPDATE clientes_cadastro
        SET due_date = CASE
            WHEN due_date <= 14 THEN 10
            WHEN due_date <= 24 THEN 20
            ELSE 30
        END
        WHERE due_date NOT IN (10, 20, 30)
        """
    )
    op.execute(
        "ALTER TABLE clientes_cadastro "
        "DROP CONSTRAINT IF EXISTS ck_cliente_cad_due_date"
    )
    op.create_check_constraint(
        "ck_cliente_cad_due_date",
        "clientes_cadastro",
        "due_date IN (10, 20, 30)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_cliente_cad_due_date",
        "clientes_cadastro",
        type_="check",
    )
    op.create_check_constraint(
        "ck_cliente_cad_due_date",
        "clientes_cadastro",
        "due_date BETWEEN 1 AND 28",
    )
    op.drop_column("clientes_cadastro", "email_encrypted")
