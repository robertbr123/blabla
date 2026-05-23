"""Avaliacao do tecnico no campo — novas colunas em cliente_app_os.

Quando OS envolveu visita presencial de tecnico, admin marca teve_visita_tecnica
ao concluir. NPS do cliente entao inclui 3 perguntas binarias extras:
- tecnico_pontual: chegou no horario?
- tecnico_educado: foi educado?
- tecnico_limpou: deixou limpo apos servico?

Revision ID: 0037_cliente_app_os_visita_tecnica
Revises: 0036_cliente_app_contatos_operadora
Create Date: 2026-05-22
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0037_cliente_app_os_visita_tecnica"
down_revision: str | None = "0036_cliente_app_contatos_operadora"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cliente_app_os",
        sa.Column(
            "teve_visita_tecnica",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "cliente_app_os",
        sa.Column("tecnico_pontual", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "cliente_app_os",
        sa.Column("tecnico_educado", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "cliente_app_os",
        sa.Column("tecnico_limpou", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cliente_app_os", "tecnico_limpou")
    op.drop_column("cliente_app_os", "tecnico_educado")
    op.drop_column("cliente_app_os", "tecnico_pontual")
    op.drop_column("cliente_app_os", "teve_visita_tecnica")
