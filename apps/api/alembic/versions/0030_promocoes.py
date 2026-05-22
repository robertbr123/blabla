"""Promoções gerenciadas pelo admin, exibidas no app cliente.

Tabelas:
- `promocoes` — cards do carrossel da home do app. Tipos: `generica` ou `indicacao`.
- `promocoes_eventos` — analytics (view/click) por cliente.

Revision ID: 0030_promocoes
Revises: 0029_cliente_app_chat_handoff
Create Date: 2026-05-21
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0030_promocoes"
down_revision: str | None = "0029_cliente_app_chat_handoff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "promocoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("titulo", sa.String(120), nullable=False),
        sa.Column("subtitulo", sa.String(240), nullable=False, server_default=""),
        sa.Column("imagem_url", sa.Text(), nullable=True),
        sa.Column("cta_label", sa.String(40), nullable=False, server_default="Saiba mais"),
        sa.Column("cta_action", sa.String(240), nullable=False, server_default="info"),
        sa.Column("tipo", sa.String(24), nullable=False, server_default="generica"),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valido_de", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valido_ate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("segmento", sa.String(64), nullable=False, server_default="todos"),
        sa.Column("gradient_from", sa.String(9), nullable=True),
        sa.Column("gradient_to", sa.String(9), nullable=True),
        sa.Column("icon", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_promocoes_ativa_ordem", "promocoes", ["ativa", "ordem"])
    op.create_index("ix_promocoes_tipo", "promocoes", ["tipo"])

    op.create_table(
        "promocoes_eventos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "promocao_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("promocoes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cliente_app_user_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("tipo", sa.String(16), nullable=False),  # view | click
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_promocoes_eventos_promo_tipo",
        "promocoes_eventos",
        ["promocao_id", "tipo"],
    )
    op.create_index(
        "ix_promocoes_eventos_user_promo",
        "promocoes_eventos",
        ["cliente_app_user_id", "promocao_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_promocoes_eventos_user_promo", table_name="promocoes_eventos")
    op.drop_index("ix_promocoes_eventos_promo_tipo", table_name="promocoes_eventos")
    op.drop_table("promocoes_eventos")
    op.drop_index("ix_promocoes_tipo", table_name="promocoes")
    op.drop_index("ix_promocoes_ativa_ordem", table_name="promocoes")
    op.drop_table("promocoes")
