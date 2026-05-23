"""Programa de fidelidade — resgates pendentes (admin aprova manualmente).

Pontos sao calculados sob demanda (tempo de casa + faturas pagas + indicacoes
aceitas) — nao tem tabela de saldo. Resgate cria pedido pendente que admin
processa via dashboard (gera desconto no SGP manualmente).

Revision ID: 0038_cliente_app_fidelidade
Revises: 0037_cliente_app_os_visita_tecnica
Create Date: 2026-05-22
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0038_cliente_app_fidelidade"
down_revision: str | None = "0037_cliente_app_os_visita_tecnica"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cliente_app_fidelidade_resgates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cliente_app_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        # Slug da recompensa: desc10 | desc20 | upgrade_temp | outro
        sa.Column("recompensa_slug", sa.String(48), nullable=False),
        sa.Column("recompensa_label", sa.String(120), nullable=False),
        sa.Column("pontos_gastos", sa.Integer(), nullable=False),
        # pendente | aprovado | aplicado | rejeitado
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'pendente'"),
        ),
        sa.Column("obs_admin", sa.Text(), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_fidelidade_resgates_user_status",
        "cliente_app_fidelidade_resgates",
        ["cliente_app_user_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_fidelidade_resgates_user_status",
        table_name="cliente_app_fidelidade_resgates",
    )
    op.drop_table("cliente_app_fidelidade_resgates")
