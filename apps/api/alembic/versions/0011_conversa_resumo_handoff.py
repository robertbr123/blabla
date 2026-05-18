"""conversas: resumo_handoff_encrypted + resumo_handoff_at.

Resumo gerado por LLM quando a conversa transita pra atendente humano. PII
criptografada com Fernet (mesma estrategia das demais colunas sensiveis).

Revision ID: 0011_conversa_resumo_handoff
Revises: 0010_os_nome_sgp
Create Date: 2026-05-18
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_conversa_resumo_handoff"
down_revision: str | None = "0010_os_nome_sgp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversas",
        sa.Column("resumo_handoff_encrypted", sa.Text(), nullable=True),
    )
    op.add_column(
        "conversas",
        sa.Column("resumo_handoff_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversas", "resumo_handoff_at")
    op.drop_column("conversas", "resumo_handoff_encrypted")
