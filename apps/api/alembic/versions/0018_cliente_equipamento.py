"""F8 — Histórico de equipamentos instalados por cliente.

Cada `saida` de item serializado feita numa OS (com `ordem_servico_id`) gera
um registro aqui. Quando o mesmo serial é `recolhido`, o registro é fechado
(removido_em / removido_em_os_id preenchidos). Isso permite ver, na ficha do
cliente, "ONU XPON ZTE serial X instalada em DD/MM/YYYY".

Itens não-serializados (cabo, conector) NÃO entram aqui — só serializados.

Revision ID: 0018_cliente_equipamento
Revises: 0017_recolhido_tipo
Create Date: 2026-05-18
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_cliente_equipamento"
down_revision: str | None = "0017_recolhido_tipo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cliente_equipamento",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cliente_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("estoque_item.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("serial", sa.String(120), nullable=False),
        sa.Column(
            "instalado_em_os_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ordens_servico.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "instalado_por_tecnico_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tecnicos.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "instalado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "removido_em",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "removido_em_os_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ordens_servico.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    # Um serial só pode estar ATIVO (removido_em IS NULL) em UM cliente por vez.
    op.create_index(
        "uq_cliente_equipamento_ativo",
        "cliente_equipamento",
        ["item_id", "serial"],
        unique=True,
        postgresql_where=sa.text("removido_em IS NULL"),
    )
    op.create_index(
        "ix_cliente_equipamento_cliente",
        "cliente_equipamento",
        ["cliente_id", "instalado_em"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cliente_equipamento_cliente", table_name="cliente_equipamento"
    )
    op.drop_index(
        "uq_cliente_equipamento_ativo", table_name="cliente_equipamento"
    )
    op.drop_table("cliente_equipamento")
