"""Tabela estoque_categoria + seed dos 5 valores legados.

Antes: categoria era string validada por regex (onu/roteador/cabo/conector/outro).
Agora: tabela CRUD para admin cadastrar quantas categorias quiser. Os valores
existentes em estoque_item.categoria continuam funcionando — apenas seedamos
a tabela com eles pra o select do dashboard listar tudo.

Revision ID: 0033_estoque_categoria
Revises: 0032_indicacao_shares_app
Create Date: 2026-05-21
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_estoque_categoria"
down_revision: str | None = "0032_indicacao_shares_app"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "estoque_categoria",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("slug", sa.String(40), nullable=False, unique=True),
        sa.Column("nome", sa.String(80), nullable=False),
        sa.Column(
            "ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    seed = [
        ("onu", "ONU"),
        ("roteador", "Roteador"),
        ("cabo", "Cabo"),
        ("conector", "Conector"),
        ("outro", "Outro"),
    ]
    for slug, nome in seed:
        op.execute(
            sa.text(
                "INSERT INTO estoque_categoria (slug, nome) VALUES (:slug, :nome) "
                "ON CONFLICT (slug) DO NOTHING"
            ).bindparams(slug=slug, nome=nome)
        )


def downgrade() -> None:
    op.drop_table("estoque_categoria")
