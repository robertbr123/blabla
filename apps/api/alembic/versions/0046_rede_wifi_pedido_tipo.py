"""rede_wifi_pedido: coluna tipo ('senha'|'reboot') pra auditar reboots.

A Fatia 3 (dashboard) permite reiniciar a ONU como acao de suporte. A auditoria
reusa rede_wifi_pedido com tipo='reboot' (a troca de senha continua 'senha').

Revision ID: 0046_rede_wifi_pedido_tipo
Revises: 0045_rede_wifi_pedido_cpf
Create Date: 2026-06-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0046_rede_wifi_pedido_tipo"
down_revision: str | None = "0045_rede_wifi_pedido_cpf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rede_wifi_pedido",
        sa.Column("tipo", sa.String(16), nullable=False, server_default="senha"),
    )


def downgrade() -> None:
    op.drop_column("rede_wifi_pedido", "tipo")
