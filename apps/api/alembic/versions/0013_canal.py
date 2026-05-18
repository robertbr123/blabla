"""F4 — Multi-instância WhatsApp: tabela canal + canal_id em conversas.

Conversas separadas por canal: o mesmo cliente em Suporte e Comercial cria
2 conversas distintas com históricos isolados. Atendentes filtram por canal.

A coluna `canal_id` nasce NULLABLE para permitir backfill seguro em produção:
conversas existentes ficam apontando pra NULL (interpretado como "canal default"
pelo runtime). Uma migração futura pode marcar NOT NULL apos backfill garantido.

Seed: o canal default é criado pelo startup do app (lifespan) com
evolution_instance vindo de settings.evolution_instance.

Revision ID: 0013_canal
Revises: 0012_cobranca_regua
Create Date: 2026-05-18
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_canal"
down_revision: str | None = "0012_cobranca_regua"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "canal",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(40), nullable=False, unique=True),
        sa.Column("nome", sa.String(80), nullable=False),
        sa.Column("evolution_instance", sa.String(80), nullable=False, unique=True),
        sa.Column(
            "prompt_variant",
            sa.String(40),
            nullable=False,
            server_default="default",
        ),
        sa.Column(
            "ativo", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("horario_inicio", sa.Time(), nullable=True),
        sa.Column("horario_fim", sa.Time(), nullable=True),
        sa.Column("msg_fora_horario", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.add_column(
        "conversas",
        sa.Column(
            "canal_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("canal.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_conversas_canal_whatsapp",
        "conversas",
        ["canal_id", "whatsapp"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_conversas_canal_whatsapp", table_name="conversas")
    op.drop_column("conversas", "canal_id")
    op.drop_table("canal")
