"""rede_wifi_pedido: auditoria de troca de senha WiFi (TR-069).

Registra o fato da troca (cliente, ONU, ator, quando) - nunca a senha.

Revision ID: 0044_rede_wifi_pedido
Revises: 0043_whatsapp_message_status
Create Date: 2026-06-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0044_rede_wifi_pedido"
down_revision: str | None = "0043_whatsapp_message_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rede_wifi_pedido",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contrato_id", sa.String(64), nullable=True),
        sa.Column("pppoe_login", sa.String(128), nullable=True),
        sa.Column("device_id", sa.String(128), nullable=False),
        sa.Column("ator_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="enviado"),
        sa.Column("reiniciou", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_rede_wifi_pedido_cliente", "rede_wifi_pedido", ["cliente_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_rede_wifi_pedido_cliente", table_name="rede_wifi_pedido")
    op.drop_table("rede_wifi_pedido")
