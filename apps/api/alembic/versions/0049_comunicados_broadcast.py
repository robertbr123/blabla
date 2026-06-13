"""Comunicados/disparo em massa: campanhas + destinatarios + templates + opt-out marketing.

Revision ID: 0049_comunicados_broadcast
Revises: 0048_promocoes_leads
Create Date: 2026-06-13
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0049_comunicados_broadcast"
down_revision: str | None = "0048_promocoes_leads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- opt-out de marketing em clientes ---
    op.add_column(
        "clientes",
        sa.Column("marketing_optout", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "clientes",
        sa.Column("marketing_optout_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- broadcast_templates ---
    op.create_table(
        "broadcast_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="pt_BR"),
        sa.Column("category", sa.String(20), nullable=False, server_default="MARKETING"),
        sa.Column("variaveis", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("header_tipo", sa.String(10), nullable=False, server_default="none"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # --- campanhas ---
    op.create_table(
        "campanhas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("titulo", sa.String(120), nullable=False),
        sa.Column(
            "canal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("canal.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("template_name", sa.String(64), nullable=False),
        sa.Column("template_language", sa.String(10), nullable=False, server_default="pt_BR"),
        sa.Column("body_params", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("header_media_url", sa.Text(), nullable=True),
        sa.Column("segmentacao", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="rascunho"),
        sa.Column("total_destinatarios", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enviadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("falhas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("agendada_para", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_campanhas_status", "campanhas", ["status"])

    # --- campanha_destinatarios ---
    op.create_table(
        "campanha_destinatarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "campanha_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campanhas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cliente_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clientes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("whatsapp", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("wamid", sa.String(80), nullable=True),
        sa.Column("erro", sa.Text(), nullable=True),
        sa.Column("enviada_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_campanha_dest_campanha_status",
        "campanha_destinatarios",
        ["campanha_id", "status"],
    )
    op.create_index("ix_campanha_dest_wamid", "campanha_destinatarios", ["wamid"])

    # --- seed dos templates iniciais (espelham o que será aprovado na Meta) ---
    bt = sa.table(
        "broadcast_templates",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("language", sa.String),
        sa.column("category", sa.String),
        sa.column("variaveis", postgresql.JSONB),
        sa.column("header_tipo", sa.String),
        sa.column("ativo", sa.Boolean),
    )
    op.bulk_insert(
        bt,
        [
            {
                "id": uuid.uuid4(),
                "name": "comunicado_geral",
                "language": "pt_BR",
                "category": "MARKETING",
                "variaveis": [{"indice": 1, "label": "Mensagem", "tipo": "texto"}],
                "header_tipo": "none",
                "ativo": True,
            },
            {
                "id": uuid.uuid4(),
                "name": "promocao",
                "language": "pt_BR",
                "category": "MARKETING",
                "variaveis": [
                    {"indice": 1, "label": "Descrição da promoção", "tipo": "texto"},
                    {"indice": 2, "label": "Link", "tipo": "url"},
                ],
                "header_tipo": "none",
                "ativo": True,
            },
            {
                "id": uuid.uuid4(),
                "name": "lancamento_app",
                "language": "pt_BR",
                "category": "MARKETING",
                "variaveis": [{"indice": 1, "label": "Link de download do app", "tipo": "url"}],
                "header_tipo": "none",
                "ativo": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_campanha_dest_wamid", table_name="campanha_destinatarios")
    op.drop_index("ix_campanha_dest_campanha_status", table_name="campanha_destinatarios")
    op.drop_table("campanha_destinatarios")
    op.drop_index("ix_campanhas_status", table_name="campanhas")
    op.drop_table("campanhas")
    op.drop_table("broadcast_templates")
    op.drop_column("clientes", "marketing_optout_at")
    op.drop_column("clientes", "marketing_optout")
