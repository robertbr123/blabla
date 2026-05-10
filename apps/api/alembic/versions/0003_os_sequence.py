"""os_sequence table for OS-YYYYMMDD-NNN daily counter.

Revision ID: 0003_os_sequence
Revises: 0002
Create Date: 2026-05-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0003_os_sequence"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "os_sequence",
        sa.Column("date", sa.Date, primary_key=True),
        sa.Column("n", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("os_sequence")
