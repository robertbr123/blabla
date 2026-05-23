"""Card do dia — engajamento entre logins.

Tabela `cliente_app_card_dia` armazena cards rotativos exibidos na Home
do app cliente. Backend escolhe 1 card/dia por usuario via hash
deterministico (mesmo card por 24h pra cada user).

Seed inicial com 7 cards pra ter conteudo do dia 1.

Revision ID: 0039_cliente_app_card_dia
Revises: 0038_cliente_app_fidelidade
Create Date: 2026-05-23
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0039_cliente_app_card_dia"
down_revision: str | None = "0038_cliente_app_fidelidade"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cliente_app_card_dia",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(48), nullable=False, unique=True),
        sa.Column("titulo", sa.String(120), nullable=False),
        sa.Column("corpo", sa.Text(), nullable=False),
        # info | url:<https> | tela:<rota> (mesmo padrao das promocoes)
        sa.Column(
            "cta_label", sa.String(48), nullable=False, server_default="Saiba mais"
        ),
        sa.Column(
            "cta_action", sa.String(255), nullable=False, server_default="info"
        ),
        # Nome icone Material (mapeado em promo_icon_map.dart do app).
        sa.Column("icon", sa.String(48), nullable=True),
        # Gradient (formato hex sem '#' ex '14B8B0').
        sa.Column("gradient_from", sa.String(8), nullable=True),
        sa.Column("gradient_to", sa.String(8), nullable=True),
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
        "ix_card_dia_ativo",
        "cliente_app_card_dia",
        ["ativo"],
    )

    # Seed inicial — 7 cards (1 pra cada dia da semana se cliente abrir
    # 7 dias seguidos).
    seeds = [
        {
            "slug": "wifi_posicao",
            "titulo": "Dica do dia: posição do roteador",
            "corpo": "Mantenha o roteador no centro da casa e longe de paredes grossas. A diferença na velocidade pode ser de até 40%.",
            "cta_label": "Mais dicas",
            "cta_action": "tela:/faq",
            "icon": "wifi_rounded",
            "gradient_from": "14B8B0",
            "gradient_to": "0F8F89",
        },
        {
            "slug": "indique_ganhe",
            "titulo": "Indique amigos e ganhe",
            "corpo": "A cada 3 amigos que fecharem plano com seu código, você ganha 1 mês grátis.",
            "cta_label": "Pegar meu código",
            "cta_action": "tela:/indicacao",
            "icon": "card_giftcard_rounded",
            "gradient_from": "E8A33D",
            "gradient_to": "FF8E53",
        },
        {
            "slug": "fidelidade_pts",
            "titulo": "Você tem pontos esperando",
            "corpo": "Cada mês de Ondeline e cada fatura paga vira pontos. Troque por descontos e meses grátis.",
            "cta_label": "Ver pontos",
            "cta_action": "tela:/fidelidade",
            "icon": "star_rounded",
            "gradient_from": "8B5CF6",
            "gradient_to": "6D28D9",
        },
        {
            "slug": "pix_rapido",
            "titulo": "Pagamento em segundos",
            "corpo": "Sua fatura tem QR Pix direto no app. Abre o app do banco, mira a câmera e pronto.",
            "cta_label": "Ir pra faturas",
            "cta_action": "tela:/faturas",
            "icon": "payments_rounded",
            "gradient_from": "3B82F6",
            "gradient_to": "1D4ED8",
        },
        {
            "slug": "suporte_24h",
            "titulo": "Internet parou? A gente resolve",
            "corpo": "Abra um chamado pelo app e acompanhe direto no chat. Sem ficar esperando no telefone.",
            "cta_label": "Abrir chamado",
            "cta_action": "tela:/suporte",
            "icon": "support_agent_rounded",
            "gradient_from": "E0455A",
            "gradient_to": "B91C1C",
        },
        {
            "slug": "reinicie_modem",
            "titulo": "Truque dos técnicos",
            "corpo": "Lenta? Desliga o modem da tomada por 30 segundos e liga de novo. Resolve 80% dos casos.",
            "cta_label": "Outras dicas",
            "cta_action": "tela:/faq",
            "icon": "flash_on_rounded",
            "gradient_from": "14B8B0",
            "gradient_to": "0B1F3A",
        },
        {
            "slug": "novidades",
            "titulo": "App sempre melhorando",
            "corpo": "Toda semana a gente adiciona algo novo. Mantenha o app atualizado pra não perder nada.",
            "cta_label": "Ver promoções",
            "cta_action": "info",
            "icon": "celebration_rounded",
            "gradient_from": "F472B6",
            "gradient_to": "BE185D",
        },
    ]

    card_dia = sa.table(
        "cliente_app_card_dia",
        sa.column("id"),
        sa.column("slug"),
        sa.column("titulo"),
        sa.column("corpo"),
        sa.column("cta_label"),
        sa.column("cta_action"),
        sa.column("icon"),
        sa.column("gradient_from"),
        sa.column("gradient_to"),
    )
    op.bulk_insert(
        card_dia,
        [{"id": uuid.uuid4(), **s} for s in seeds],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_card_dia_ativo",
        table_name="cliente_app_card_dia",
    )
    op.drop_table("cliente_app_card_dia")
