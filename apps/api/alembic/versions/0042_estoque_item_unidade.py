"""Estoque: unidade de medida no item (UN/metro/CX/PC).

Adiciona ``unidade`` em ``estoque_item`` pra o app saber como exibir/inserir a
quantidade (rotulo + digitar livre). Quantidade segue sempre INTEIRA — unidade
e apenas semantica/exibicao, sem mudanca na logica de movimento/saldo.

- ``unidade``: NOT NULL, default 'UN'. Backfill automatico ('UN') pra todos os
  itens existentes — zero impacto.

Revision ID: 0042_estoque_item_unidade
Revises: 0041_canal_whatsapp_provider
Create Date: 2026-05-26
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0042_estoque_item_unidade"
down_revision: str | None = "0041_canal_whatsapp_provider"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "estoque_item",
        sa.Column(
            "unidade",
            sa.String(10),
            nullable=False,
            server_default="UN",
        ),
    )


def downgrade() -> None:
    op.drop_column("estoque_item", "unidade")
