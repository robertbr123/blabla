"""F7 — Bot por voz: transcricao em mensagens + aviso ASR em clientes.

`mensagens.transcricao_encrypted` guarda o texto transcrito (Fernet, PII).
`mensagens.transcricao_status` rastreia o ciclo: pending → ok | failed | skipped.

`clientes.asr_aviso_enviado_at` marca quando o aviso LGPD de transcricao foi
enviado pra esse cliente (idempotente, nao repete em audios seguintes).

Revision ID: 0016_mensagem_transcricao
Revises: 0015_estoque
Create Date: 2026-05-18
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_mensagem_transcricao"
down_revision: str | None = "0015_estoque"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mensagens",
        sa.Column("transcricao_encrypted", sa.Text(), nullable=True),
    )
    op.add_column(
        "mensagens",
        sa.Column("transcricao_status", sa.String(16), nullable=True),
    )
    op.add_column(
        "clientes",
        sa.Column("asr_aviso_enviado_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("clientes", "asr_aviso_enviado_at")
    op.drop_column("mensagens", "transcricao_status")
    op.drop_column("mensagens", "transcricao_encrypted")
