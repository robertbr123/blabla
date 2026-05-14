"""os_followup_reatribuicao — new fields for follow-up and reassignment.

Revision ID: 0005_os_followup_reatribuicao
Revises: 0004
Create Date: 2026-05-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID

revision: str = "0005_os_followup_reatribuicao"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # ordens_servico: reatribuição
    op.add_column("ordens_servico", sa.Column("reatribuido_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ordens_servico", sa.Column(
        "reatribuido_por", PgUUID(as_uuid=True), nullable=True
    ))
    op.create_foreign_key(
        "fk_os_reatribuido_por_users",
        "ordens_servico", "users",
        ["reatribuido_por"], ["id"],
        ondelete="SET NULL",
    )
    op.add_column("ordens_servico", sa.Column(
        "historico_reatribuicoes", JSONB, nullable=True, server_default=text("'[]'::jsonb")
    ))

    # ordens_servico: follow-up
    op.add_column("ordens_servico", sa.Column("follow_up_resposta", sa.Text, nullable=True))
    op.add_column("ordens_servico", sa.Column("follow_up_respondido_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ordens_servico", sa.Column("follow_up_resultado", sa.String(20), nullable=True))

    # conversas: follow-up OS reference
    op.add_column("conversas", sa.Column("followup_os_id", PgUUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_conversas_followup_os",
        "conversas", "ordens_servico",
        ["followup_os_id"], ["id"],
        ondelete="SET NULL",
    )

    # widen conversas.estado varchar to accommodate 'aguarda_followup_os' (19 chars)
    # conversa_estado is a non-native enum (varchar), so no ALTER TYPE needed
    op.alter_column(
        "conversas", "estado",
        existing_type=sa.String(17),
        type_=sa.String(20),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.drop_constraint("fk_conversas_followup_os", "conversas", type_="foreignkey")
    op.drop_column("conversas", "followup_os_id")
    op.drop_constraint("fk_os_reatribuido_por_users", "ordens_servico", type_="foreignkey")
    op.drop_column("ordens_servico", "reatribuido_em")
    op.drop_column("ordens_servico", "reatribuido_por")
    op.drop_column("ordens_servico", "historico_reatribuicoes")
    op.drop_column("ordens_servico", "follow_up_resposta")
    op.drop_column("ordens_servico", "follow_up_respondido_em")
    op.drop_column("ordens_servico", "follow_up_resultado")
    # WARNING: will fail if any row holds a value longer than 17 chars (e.g. 'aguarda_followup_os').
    op.alter_column(
        "conversas", "estado",
        existing_type=sa.String(20),
        type_=sa.String(17),
        existing_nullable=False,
    )
