"""rede_wifi_pedido: identificacao por cpf_hash (cliente_id vira opcional).

A troca de senha WiFi passa a localizar o cliente por CPF -> SGP -> pppoe
(cobre clientes antigos que so existem no SGP, sem cadastro local). Auditoria
guarda cpf_hash (PII-safe) em vez de exigir um id de cliente local.

Revision ID: 0045_rede_wifi_pedido_cpf
Revises: 0044_rede_wifi_pedido
Create Date: 2026-06-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0045_rede_wifi_pedido_cpf"
down_revision: str | None = "0044_rede_wifi_pedido"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rede_wifi_pedido",
        sa.Column("cpf_hash", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_rede_wifi_pedido_cpf_hash", "rede_wifi_pedido", ["cpf_hash"]
    )
    op.alter_column("rede_wifi_pedido", "cliente_id", nullable=True)


def downgrade() -> None:
    op.alter_column("rede_wifi_pedido", "cliente_id", nullable=False)
    op.drop_index("ix_rede_wifi_pedido_cpf_hash", table_name="rede_wifi_pedido")
    op.drop_column("rede_wifi_pedido", "cpf_hash")
