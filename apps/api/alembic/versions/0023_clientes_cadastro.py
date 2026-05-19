"""Clientes cadastrados em campo pelo tecnico.

Tabela separada da `clientes` (que e cache do SGP). Esta tabela e fonte
primaria da instalacao: gravada pelo tecnico, depois sincronizada com
SGP. PII encriptado seguindo o padrao do projeto.

Tambem adiciona estoque_movimento.cliente_cadastro_id pra rastrear baixa
de material por instalacao.

Revision ID: 0023_clientes_cadastro
Revises: 0022_users_foto
Create Date: 2026-05-19
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023_clientes_cadastro"
down_revision: str | None = "0022_users_foto"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clientes_cadastro",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # PII (encrypted + hash)
        sa.Column("cpf_hash", sa.String(length=64), nullable=False),
        sa.Column("cpf_encrypted", sa.Text(), nullable=False),
        sa.Column("nome_encrypted", sa.Text(), nullable=False),
        sa.Column("dob", sa.Date(), nullable=False),
        sa.Column("telefone_encrypted", sa.Text(), nullable=False),
        # Endereco (plain — searchable)
        sa.Column("cep", sa.String(length=10), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("number", sa.String(length=10), nullable=False),
        sa.Column("complement", sa.String(length=255), nullable=True),
        sa.Column("neighborhood", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=True),
        # Plano + conexao
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("plan_nome", sa.String(length=255), nullable=False),
        sa.Column("pppoe_user_encrypted", sa.Text(), nullable=True),
        sa.Column("pppoe_pass_encrypted", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Integer(), nullable=False),  # 1-28
        # Instalador (FK opcional + nome cacheado)
        sa.Column(
            "installer_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("installer_nome", sa.String(length=255), nullable=False),
        # Equipamento + contrato + obs
        sa.Column("serial", sa.String(length=100), nullable=True),
        sa.Column("contrato", sa.String(length=20), nullable=True),
        sa.Column("observation", sa.Text(), nullable=True),
        # Geo da instalacao
        sa.Column("latitude", sa.Numeric(10, 8), nullable=True),
        sa.Column("longitude", sa.Numeric(11, 8), nullable=True),
        sa.Column("location_accuracy", sa.Numeric(10, 2), nullable=True),
        # Fotos (lista de {url, ts, size, mime, tipo})
        sa.Column("fotos", postgresql.JSONB(), nullable=True),
        # Audit + sync SGP
        sa.Column("registration_date", sa.Date(), nullable=False),
        sa.Column("sgp_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sgp_id", sa.String(length=40), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("due_date BETWEEN 1 AND 28", name="ck_cliente_cad_due_date"),
    )
    op.create_index(
        "ix_clientes_cadastro_cpf_hash",
        "clientes_cadastro",
        ["cpf_hash"],
        unique=True,
    )
    op.create_index(
        "ix_clientes_cadastro_city",
        "clientes_cadastro",
        ["city"],
    )
    op.create_index(
        "ix_clientes_cadastro_serial",
        "clientes_cadastro",
        ["serial"],
    )
    op.create_index(
        "ix_clientes_cadastro_location",
        "clientes_cadastro",
        ["latitude", "longitude"],
    )
    op.create_index(
        "ix_clientes_cadastro_installer",
        "clientes_cadastro",
        ["installer_user_id"],
    )
    op.create_index(
        "ix_clientes_cadastro_sync",
        "clientes_cadastro",
        ["sgp_synced_at"],
    )
    op.create_index(
        "ix_clientes_cadastro_deleted",
        "clientes_cadastro",
        ["deleted_at"],
    )

    # Link com baixa de material em estoque_movimento.
    op.add_column(
        "estoque_movimento",
        sa.Column(
            "cliente_cadastro_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clientes_cadastro.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_estoque_mov_cliente_cadastro",
        "estoque_movimento",
        ["cliente_cadastro_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_estoque_mov_cliente_cadastro", table_name="estoque_movimento"
    )
    op.drop_column("estoque_movimento", "cliente_cadastro_id")
    op.drop_index("ix_clientes_cadastro_deleted", table_name="clientes_cadastro")
    op.drop_index("ix_clientes_cadastro_sync", table_name="clientes_cadastro")
    op.drop_index("ix_clientes_cadastro_installer", table_name="clientes_cadastro")
    op.drop_index("ix_clientes_cadastro_location", table_name="clientes_cadastro")
    op.drop_index("ix_clientes_cadastro_serial", table_name="clientes_cadastro")
    op.drop_index("ix_clientes_cadastro_city", table_name="clientes_cadastro")
    op.drop_index("ix_clientes_cadastro_cpf_hash", table_name="clientes_cadastro")
    op.drop_table("clientes_cadastro")
