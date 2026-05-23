"""Missoes — Fase 3d engajamento.

Tabela `cliente_app_missao_completada` registra cada conclusao discreta
de missao (com timestamp). Slug do tipo:
- 'share_indicacao:YYYY-MM-DD' — 1x/dia max (unique)
- 'responder_nps:<os_id>'      — 1x por OS (unique)

A missao 'pagar_em_dia' nao usa tabela — e calculada on-the-fly a partir
do SGP cache (numero de titulos pagos com dias_atraso=0).

Revision ID: 0040_cliente_app_missoes
Revises: 0039_cliente_app_card_dia
Create Date: 2026-05-23
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0040_cliente_app_missoes"
down_revision: str | None = "0039_cliente_app_card_dia"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cliente_app_missao_completada",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cliente_app_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        # Slug completo da missao concluida. Inclui chave de unicidade
        # (data ou os_id) pra evitar dupla contagem.
        sa.Column("slug", sa.String(96), nullable=False),
        sa.Column(
            "completada_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_missao_user_slug",
        "cliente_app_missao_completada",
        ["cliente_app_user_id", "slug"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_missao_user_slug",
        table_name="cliente_app_missao_completada",
    )
    op.drop_table("cliente_app_missao_completada")
