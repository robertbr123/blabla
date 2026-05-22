"""Handoff humano no chat in-app do cliente.

Quando `human_handoff_atendente_id IS NOT NULL`, o bot LLM nao responde
automaticamente; atendente conduz a conversa. Atendente "libera" pelo
dashboard pra bot voltar a responder.

Revision ID: 0029_cliente_app_chat_handoff
Revises: 0028_cliente_app_messages
Create Date: 2026-05-22
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0029_cliente_app_chat_handoff"
down_revision: str | None = "0028_cliente_app_messages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cliente_app_users",
        sa.Column("human_handoff_atendente_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "cliente_app_users",
        sa.Column("human_handoff_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cliente_app_users_handoff_atendente",
        "cliente_app_users",
        "users",
        ["human_handoff_atendente_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_cliente_app_users_handoff_atendente",
        "cliente_app_users",
        type_="foreignkey",
    )
    op.drop_column("cliente_app_users", "human_handoff_at")
    op.drop_column("cliente_app_users", "human_handoff_atendente_id")
