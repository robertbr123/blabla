"""F6+ — Adicionar tipo 'recolhido' ao enum de movimento de estoque.

`recolhido` = equipamento removido da casa do cliente entra no estoque do
técnico (cliente → técnico, +saldo). Usado em trocas — técnico instala
equipamento novo (saida) e leva o velho de volta (recolhido).

Revision ID: 0017_recolhido_tipo
Revises: 0016_mensagem_transcricao
Create Date: 2026-05-18
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0017_recolhido_tipo"
down_revision: str | None = "0016_mensagem_transcricao"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_estoque_tipo_enum", "estoque_movimento", type_="check"
    )
    op.create_check_constraint(
        "ck_estoque_tipo_enum",
        "estoque_movimento",
        "tipo IN ('entrada','saida','devolucao','perda',"
        "'ajuste_positivo','ajuste_negativo','recolhido')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_estoque_tipo_enum", "estoque_movimento", type_="check"
    )
    op.create_check_constraint(
        "ck_estoque_tipo_enum",
        "estoque_movimento",
        "tipo IN ('entrada','saida','devolucao','perda',"
        "'ajuste_positivo','ajuste_negativo')",
    )
