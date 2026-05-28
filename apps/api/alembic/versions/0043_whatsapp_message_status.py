"""whatsapp_message_status: tracking de delivered/read/failed de outbound Cloud.

Tabela alimentada por dois lados:

- INSERT na hora do envio (notify_sender e cliente_app_otp): grava
  ``wamid``, ``template_name``, ``recipient_jid`` e ``sent_at = now()``.
- UPDATE quando chega status update no webhook Cloud
  (api/webhook_cloud.py): preenche ``delivered_at`` / ``read_at`` /
  ``failed_at`` + ``error`` correspondente.

Sem ``last_status`` desnormalizado — derivamos do conjunto de timestamps
na hora da query (agregacao por template_name vira count com filtros NULL).

Indexes:
- UNIQUE em ``wamid`` (chave natural; usado no UPDATE pelo webhook).
- ``(template_name, sent_at)`` pra agregar metricas por template + janela
  temporal.

Revision ID: 0043_whatsapp_message_status
Revises: 0042_estoque_item_unidade
Create Date: 2026-05-28
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0043_whatsapp_message_status"
down_revision: str | None = "0042_estoque_item_unidade"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_message_status",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("wamid", sa.String(80), nullable=False, unique=True),
        sa.Column("template_name", sa.String(64), nullable=True),
        sa.Column("recipient_jid", sa.String(40), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", postgresql.JSONB, nullable=True),
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
    )
    op.create_index(
        "ix_whatsapp_message_status_template_sent",
        "whatsapp_message_status",
        ["template_name", "sent_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_whatsapp_message_status_template_sent",
        table_name="whatsapp_message_status",
    )
    op.drop_table("whatsapp_message_status")
