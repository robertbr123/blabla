"""users.foto_b64 — foto de perfil (JPEG 256x256 em base64).

Revision ID: 0022_users_foto
Revises: 0021_device_tokens
Create Date: 2026-05-19
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_users_foto"
down_revision: str | None = "0021_device_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("foto_b64", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "foto_b64")
