"""Notificacoes do app cliente.

Tabela `cliente_app_notificacoes` (historico por usuario).
Tabela `cliente_app_notif_prefs` (preferencias por categoria, key-value).

Revision ID: 0034_cliente_app_notificacoes
Revises: 0033_estoque_categoria
Create Date: 2026-05-22
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0034_cliente_app_notificacoes"
down_revision: str | None = "0033_estoque_categoria"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cliente_app_notificacoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cliente_app_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        # 'fatura' | 'os' | 'manutencao' | 'promocao' | 'conta' | 'outro'
        sa.Column("categoria", sa.String(24), nullable=False),
        sa.Column("titulo", sa.String(120), nullable=False),
        sa.Column("corpo", sa.Text(), nullable=False, server_default=""),
        # Rota interna ou URL externa (formato compativel com promocoes.cta_action).
        sa.Column("action", sa.String(240), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("lida_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_cliente_app_notif_user_created",
        "cliente_app_notificacoes",
        ["cliente_app_user_id", "created_at"],
    )
    op.create_index(
        "ix_cliente_app_notif_user_unread",
        "cliente_app_notificacoes",
        ["cliente_app_user_id", "lida_em"],
    )

    op.create_table(
        "cliente_app_notif_prefs",
        sa.Column(
            "cliente_app_user_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        # JSON {fatura: bool, os: bool, manutencao: bool, promocao: bool, conta: bool}
        sa.Column(
            "categorias",
            postgresql.JSONB(),
            nullable=False,
            # IMPORTANTE: espaco depois de ':' obrigatorio — SQLAlchemy text()
            # interpreta ':nome' como bind param e quebra o JSON.
            server_default=sa.text(
                "'{\"fatura\": true, \"os\": true, \"manutencao\": true, \"promocao\": true, \"conta\": true}'::jsonb"
            ),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("cliente_app_notif_prefs")
    op.drop_index(
        "ix_cliente_app_notif_user_unread",
        table_name="cliente_app_notificacoes",
    )
    op.drop_index(
        "ix_cliente_app_notif_user_created",
        table_name="cliente_app_notificacoes",
    )
    op.drop_table("cliente_app_notificacoes")
