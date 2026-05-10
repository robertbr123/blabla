"""widen whatsapp columns from String(20) to String(64)

Real Evolution WhatsApp JIDs are 28+ chars (e.g. 5511999999999@s.whatsapp.net)
and group JIDs are longer still (5511999999999-1234567890@g.us).
String(20) blocks production webhook ingestion.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-10

NOTE: downgrade() reverses the column widths.  If any row already contains a
value longer than 20 chars the ALTER will fail with a value-too-long error.
Truncate or back-fill before running downgrade() on production data.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0002'
down_revision: str | Sequence[str] | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        'clientes', 'whatsapp',
        existing_type=sa.String(length=20),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
    op.alter_column(
        'conversas', 'whatsapp',
        existing_type=sa.String(length=20),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
    op.alter_column(
        'leads', 'whatsapp',
        existing_type=sa.String(length=20),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
    op.alter_column(
        'tecnicos', 'whatsapp',
        existing_type=sa.String(length=20),
        type_=sa.String(length=64),
        existing_nullable=True,
    )


def downgrade() -> None:
    # WARNING: will fail if any existing value exceeds 20 chars.
    # Truncate or back-fill before running on production data.
    op.alter_column(
        'tecnicos', 'whatsapp',
        existing_type=sa.String(length=64),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
    op.alter_column(
        'leads', 'whatsapp',
        existing_type=sa.String(length=64),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
    op.alter_column(
        'conversas', 'whatsapp',
        existing_type=sa.String(length=64),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
    op.alter_column(
        'clientes', 'whatsapp',
        existing_type=sa.String(length=64),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
