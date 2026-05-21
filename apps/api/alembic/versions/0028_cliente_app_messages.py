"""Mensagens de chat in-app entre cliente e bot.

Tabela separada de `mensagens` (que e WhatsApp + Conversa). Aqui sao
apenas user/bot turns. Conteudo encriptado seguindo padrao PII.

Revision ID: 0028_cliente_app_messages
Revises: 0027_cliente_app_os
Create Date: 2026-05-21
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028_cliente_app_messages"
down_revision: str | None = "0027_cliente_app_os"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cliente_app_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cliente_app_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cliente_app_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=16), nullable=False),  # user | bot
        sa.Column("content_encrypted", sa.Text(), nullable=False),
        sa.Column("llm_tokens_used", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_cliente_app_messages_user_at",
        "cliente_app_messages",
        ["cliente_app_user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_cliente_app_messages_user_at", table_name="cliente_app_messages")
    op.drop_table("cliente_app_messages")
