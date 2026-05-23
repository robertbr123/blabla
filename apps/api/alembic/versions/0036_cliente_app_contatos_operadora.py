"""Contatos da operadora — Fale conosco no app cliente.

Tabela `cliente_app_contatos_operadora` armazena os meios de contato
exibidos no app (WhatsApp 24h, telefone emergencia, endereco, redes sociais).
Admin edita via dashboard, cliente le via GET publico autenticado.

Revision ID: 0036_cliente_app_contatos_operadora
Revises: 0035_cliente_app_os_nps
Create Date: 2026-05-22
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0036_cliente_app_contatos_operadora"
down_revision: str | None = "0035_cliente_app_os_nps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cliente_app_contatos_operadora",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # whatsapp | telefone | email | endereco | instagram | facebook |
        # site | outro
        sa.Column("tipo", sa.String(24), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        # Para tipo=endereco, valor pode ser texto livre. Para whatsapp/
        # telefone, valor e o numero (so digitos). Para urls, valor e a URL.
        sa.Column("valor", sa.Text(), nullable=False),
        # Subtitle opcional ("Horario: seg-sex 8h-18h", "Atendimento 24h").
        sa.Column("subtitle", sa.String(240), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "ativo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
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
        "ix_contatos_operadora_ativo_ordem",
        "cliente_app_contatos_operadora",
        ["ativo", "ordem"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_contatos_operadora_ativo_ordem",
        table_name="cliente_app_contatos_operadora",
    )
    op.drop_table("cliente_app_contatos_operadora")
