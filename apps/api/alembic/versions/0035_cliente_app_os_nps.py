"""NPS pos-OS — colunas em cliente_app_os.

Adiciona campos pra pesquisa de satisfacao (0-10) apos OS concluida:
- nps_solicitado_em: quando o backend pediu a avaliacao (push enviado).
- nps_respondido_em: quando o cliente respondeu.
- nps_score: nota 0-10.
- nps_comentario: comentario opcional.

Revision ID: 0035_cliente_app_os_nps
Revises: 0034_cliente_app_notificacoes
Create Date: 2026-05-22
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035_cliente_app_os_nps"
down_revision: str | None = "0034_cliente_app_notificacoes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cliente_app_os",
        sa.Column("nps_solicitado_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "cliente_app_os",
        sa.Column("nps_respondido_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "cliente_app_os",
        sa.Column("nps_score", sa.Integer(), nullable=True),
    )
    op.add_column(
        "cliente_app_os",
        sa.Column("nps_comentario", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "ck_cliente_app_os_nps_score_range",
        "cliente_app_os",
        "nps_score IS NULL OR (nps_score BETWEEN 0 AND 10)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_cliente_app_os_nps_score_range", "cliente_app_os", type_="check"
    )
    op.drop_column("cliente_app_os", "nps_comentario")
    op.drop_column("cliente_app_os", "nps_score")
    op.drop_column("cliente_app_os", "nps_respondido_em")
    op.drop_column("cliente_app_os", "nps_solicitado_em")
