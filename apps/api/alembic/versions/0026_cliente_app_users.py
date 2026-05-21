"""Cliente app users — tabela de usuarios do app do cliente final.

Separada de `users` (staff). cpf_hash unico identifica o cliente,
cpf_encrypted/nome_encrypted/telefone_encrypted seguem padrao PII do
projeto. cliente_app_otp armazena codigos efemeros (10min) com hash.

Revision ID: 0026_cliente_app_users
Revises: 0025_nome_normalized
Create Date: 2026-05-21
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026_cliente_app_users"
down_revision: str | None = "0025_nome_normalized"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cliente_app_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cpf_hash", sa.String(length=64), nullable=False),
        sa.Column("cpf_last4", sa.String(length=4), nullable=False),
        sa.Column("cpf_encrypted", sa.Text(), nullable=False),
        sa.Column("nome_encrypted", sa.Text(), nullable=False),
        sa.Column("telefone_encrypted", sa.Text(), nullable=False),
        sa.Column("email_encrypted", sa.Text(), nullable=True),
        sa.Column("sgp_id", sa.String(length=64), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("push_token", sa.String(length=512), nullable=True),
        sa.Column("biometric_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'pending_otp'"),
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_cliente_app_users_cpf_hash", "cliente_app_users", ["cpf_hash"], unique=True)
    op.create_index("ix_cliente_app_users_sgp_id", "cliente_app_users", ["sgp_id"])

    op.create_table(
        "cliente_app_otp",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cpf_hash", sa.String(length=64), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=16), nullable=False),  # register|reset_pwd
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_cliente_app_otp_cpf_hash", "cliente_app_otp", ["cpf_hash"])


def downgrade() -> None:
    op.drop_index("ix_cliente_app_otp_cpf_hash", table_name="cliente_app_otp")
    op.drop_table("cliente_app_otp")
    op.drop_index("ix_cliente_app_users_sgp_id", table_name="cliente_app_users")
    op.drop_index("ix_cliente_app_users_cpf_hash", table_name="cliente_app_users")
    op.drop_table("cliente_app_users")
