"""Canal multi-provider: Evolution + WhatsApp Cloud API (Meta).

Adiciona suporte a multiplos providers de WhatsApp por canal:

- ``provider``: discriminador ('evolution' | 'cloud'). Default 'evolution' garante
  zero impacto em canais existentes.
- ``cloud_phone_id``: phone_number_id do Meta (usado pra rotear webhook inbound
  e pra construir a URL de envio outbound).
- ``cloud_waba_id``: whatsapp_business_account_id do Meta (usado pra listar
  templates aprovados).
- ``evolution_instance``: passa a ser NULLABLE — canal com provider='cloud' nao
  usa instancia Evolution. Constraint cuida da exclusividade por provider.

CHECK constraints garantem coerencia: canal Evolution exige evolution_instance,
canal Cloud exige cloud_phone_id.

Revision ID: 0041_canal_whatsapp_provider
Revises: 0040_cliente_app_missoes
Create Date: 2026-05-25
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0041_canal_whatsapp_provider"
down_revision: str | None = "0040_cliente_app_missoes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # provider — NOT NULL com default 'evolution'; backfill automatico pra linhas existentes.
    op.add_column(
        "canal",
        sa.Column(
            "provider",
            sa.String(20),
            nullable=False,
            server_default="evolution",
        ),
    )

    # Campos especificos da Cloud API (Meta). Nullable — preenchidos so quando
    # provider='cloud'.
    op.add_column("canal", sa.Column("cloud_phone_id", sa.String(40), nullable=True))
    op.add_column("canal", sa.Column("cloud_waba_id", sa.String(40), nullable=True))

    # evolution_instance vira nullable. Drop do UNIQUE pq alguns providers
    # nao tem (Cloud). Vamos recriar como UNIQUE parcial via index.
    op.alter_column("canal", "evolution_instance", existing_type=sa.String(80), nullable=True)
    op.drop_constraint("canal_evolution_instance_key", "canal", type_="unique")
    op.create_index(
        "ix_canal_evolution_instance_unique",
        "canal",
        ["evolution_instance"],
        unique=True,
        postgresql_where=sa.text("evolution_instance IS NOT NULL"),
    )

    # UNIQUE parcial em cloud_phone_id (so quando preenchido).
    op.create_index(
        "ix_canal_cloud_phone_id_unique",
        "canal",
        ["cloud_phone_id"],
        unique=True,
        postgresql_where=sa.text("cloud_phone_id IS NOT NULL"),
    )

    # Coerencia: provider='evolution' exige evolution_instance; provider='cloud' exige cloud_phone_id.
    op.create_check_constraint(
        "ck_canal_provider_fields",
        "canal",
        "(provider = 'evolution' AND evolution_instance IS NOT NULL) "
        "OR (provider = 'cloud' AND cloud_phone_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_canal_provider_fields", "canal", type_="check")
    op.drop_index("ix_canal_cloud_phone_id_unique", table_name="canal")
    op.drop_index("ix_canal_evolution_instance_unique", table_name="canal")
    op.create_unique_constraint(
        "canal_evolution_instance_key", "canal", ["evolution_instance"]
    )
    op.alter_column("canal", "evolution_instance", existing_type=sa.String(80), nullable=False)
    op.drop_column("canal", "cloud_waba_id")
    op.drop_column("canal", "cloud_phone_id")
    op.drop_column("canal", "provider")
