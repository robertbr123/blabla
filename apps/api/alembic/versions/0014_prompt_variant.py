"""F5 — A/B test de prompts: tabela prompt_variant + Conversa.prompt_variant.

Cada variante tem `trafego_pct` (0-100) — bucketing por hash(whatsapp) % 100
distribui clientes deterministicamente. Mesma whatsapp sempre cai na mesma
variante (consistencia entre conversas).

Soma de tráfego das variantes ativas deve ser ≤ 100. O resto cai em 'default'
(SYSTEM_PROMPT hardcoded no llm_loop).

Revision ID: 0014_prompt_variant
Revises: 0013_canal
Create Date: 2026-05-18
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_prompt_variant"
down_revision: str | None = "0013_canal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prompt_variant",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nome", sa.String(40), nullable=False, unique=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column(
            "ativo", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "trafego_pct", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("canal_slug", sa.String(40), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "trafego_pct >= 0 AND trafego_pct <= 100", name="ck_trafego_pct_range"
        ),
    )

    op.add_column(
        "conversas",
        sa.Column("prompt_variant", sa.String(40), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversas", "prompt_variant")
    op.drop_table("prompt_variant")
