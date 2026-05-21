"""OS abertas pelo cliente final via app.

Separada de `ordens_servico` (que e fluxo do tecnico). Aqui o cliente
solicita: sem internet, mudanca de endereco ou troca de plano. Admin
trata via dashboard (endpoint admin fica pra fase futura).

Revision ID: 0027_cliente_app_os
Revises: 0026_cliente_app_users
Create Date: 2026-05-21
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027_cliente_app_os"
down_revision: str | None = "0026_cliente_app_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cliente_app_os",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cliente_app_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cliente_app_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(length=24), nullable=False),  # sem_internet|mudanca_endereco|troca_plano
        sa.Column("descricao", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("payload_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'aberto'")),
        sa.Column("sgp_protocolo_id", sa.String(length=64), nullable=True),
        sa.Column(
            "atendente_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_cliente_app_os_user",
        "cliente_app_os",
        ["cliente_app_user_id", "created_at"],
    )
    op.create_index(
        "ix_cliente_app_os_status_admin",
        "cliente_app_os",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_cliente_app_os_status_admin", table_name="cliente_app_os")
    op.drop_index("ix_cliente_app_os_user", table_name="cliente_app_os")
    op.drop_table("cliente_app_os")
