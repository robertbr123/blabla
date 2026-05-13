"""create mensagens partitions for 2026-07 through 2026-09

Revision ID: 0004
Revises: 0003_os_sequence
Create Date: 2026-05-13
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003_os_sequence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_PARTITIONS = [
    ("mensagens_2026_07", "2026-07-01", "2026-08-01"),
    ("mensagens_2026_08", "2026-08-01", "2026-09-01"),
    ("mensagens_2026_09", "2026-09-01", "2026-10-01"),
]


def upgrade() -> None:
    for name, start, end in _PARTITIONS:
        op.execute(f"""
            CREATE TABLE IF NOT EXISTS {name} PARTITION OF mensagens
            FOR VALUES FROM ('{start}') TO ('{end}')
        """)


def downgrade() -> None:
    for name, _, _ in reversed(_PARTITIONS):
        op.execute(f"DROP TABLE IF EXISTS {name}")
