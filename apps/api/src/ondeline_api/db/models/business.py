"""Business-domain ORM models: clientes, conversas, mensagens, OS, etc.

Mensagens e particionada por mes — a particao em si e definida no migration
inicial via op.execute(). O modelo aqui declara as colunas; o postgresql_partition_by
fica em __table_args__ para o autogenerate gerar a clausula PARTITION BY.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from ondeline_api.db.base import Base


class ConversaEstado(StrEnum):
    INICIO = "inicio"
    AGUARDA_OPCAO = "aguarda_opcao"
    LEAD_NOME = "lead_nome"
    LEAD_INTERESSE = "lead_interesse"
    CLIENTE_CPF = "cliente_cpf"
    CLIENTE = "cliente"
    AGUARDA_ATENDENTE = "aguarda_atendente"
    HUMANO = "humano"
    ENCERRADA = "encerrada"
    AGUARDA_FOLLOWUP_OS = "aguarda_followup_os"
    MUDANCA_ENDERECO = "mudanca_endereco"
    CHECKLIST_OS = "checklist_os"


class ConversaStatus(StrEnum):
    BOT = "bot"
    AGUARDANDO = "aguardando"
    HUMANO = "humano"
    ENCERRADA = "encerrada"


class MensagemRole(StrEnum):
    CLIENTE = "cliente"
    BOT = "bot"
    ATENDENTE = "atendente"


class OsStatus(StrEnum):
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


class LeadStatus(StrEnum):
    NOVO = "novo"
    CONTATO = "contato"
    CONVERTIDO = "convertido"
    PERDIDO = "perdido"


class NotificacaoTipo(StrEnum):
    VENCIMENTO = "vencimento"
    ATRASO = "atraso"
    PAGAMENTO = "pagamento"
    OS_CONCLUIDA = "os_concluida"
    MANUTENCAO = "manutencao"


class NotificacaoStatus(StrEnum):
    PENDENTE = "pendente"
    ENVIADA = "enviada"
    FALHA = "falha"
    CANCELADA = "cancelada"


class SgpProvider(StrEnum):
    ONDELINE = "ondeline"
    LINKNETAM = "linknetam"


# ════════ Clientes (PII encrypted) ════════

class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    cpf_cnpj_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    cpf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    nome_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    whatsapp: Mapped[str] = mapped_column(String(64), nullable=False)
    plano: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    endereco_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    cidade: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sgp_provider: Mapped[SgpProvider | None] = mapped_column(
        Enum(SgpProvider, name="sgp_provider", native_enum=False), nullable=True
    )
    sgp_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retention_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index(
            "ix_clientes_cpf_hash",
            "cpf_hash",
            postgresql_where="deleted_at IS NULL",
        ),
        Index(
            "ix_clientes_retention",
            "retention_until",
            postgresql_where="deleted_at IS NULL",
        ),
        Index("ix_clientes_whatsapp", "whatsapp"),
    )


# ════════ Conversas + Mensagens ════════

class Conversa(Base):
    __tablename__ = "conversas"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    cliente_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True
    )
    whatsapp: Mapped[str] = mapped_column(String(64), nullable=False)
    estado: Mapped[ConversaEstado] = mapped_column(
        Enum(ConversaEstado, name="conversa_estado", native_enum=False),
        nullable=False,
        default=ConversaEstado.INICIO,
    )
    atendente_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[ConversaStatus] = mapped_column(
        Enum(ConversaStatus, name="conversa_status", native_enum=False),
        nullable=False,
        default=ConversaStatus.BOT,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retention_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    followup_os_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ordens_servico.id", ondelete="SET NULL"), nullable=True
    )
    transferred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    first_response_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    sla_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    checklist_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index(
            "ix_conversas_whatsapp",
            "whatsapp",
            postgresql_where="deleted_at IS NULL",
        ),
        Index("ix_conversas_status_last", "status", "last_message_at"),
    )


class Mensagem(Base):
    """Particionada por mes (RANGE em created_at).

    Particionamento e configurado no migration inicial via op.execute().
    Aqui declaramos schema que se aplica a tabela-pai e a cada particao.
    """

    __tablename__ = "mensagens"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), default=uuid4)
    conversa_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("conversas.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    role: Mapped[MensagemRole] = mapped_column(
        Enum(MensagemRole, name="mensagem_role", native_enum=False), nullable=False
    )
    content_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    llm_tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_tools_called: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # PK composta para suportar particionamento por created_at
        PrimaryKeyConstraint("id", "created_at", name="pk_mensagens"),
        Index("ix_mensagens_conversa", "conversa_id", "created_at"),
        {"postgresql_partition_by": "RANGE (created_at)"},
    )


# ════════ Leads ════════

class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    whatsapp: Mapped[str] = mapped_column(String(64), nullable=False)
    interesse: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, name="lead_status", native_enum=False),
        nullable=False,
        default=LeadStatus.NOVO,
    )
    atendente_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (Index("ix_leads_status", "status"),)


# ════════ Tecnicos ════════

class Tecnico(Base):
    __tablename__ = "tecnicos"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    whatsapp: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    gps_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_tecnicos_user", "user_id", unique=True),
    )


class TecnicoArea(Base):
    """N:N tecnico x area de atuacao (cidade + rua)."""

    __tablename__ = "tecnico_areas"

    tecnico_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tecnicos.id", ondelete="CASCADE"),
        nullable=False,
    )
    cidade: Mapped[str] = mapped_column(String(80), nullable=False)
    rua: Mapped[str] = mapped_column(String(120), nullable=False)
    prioridade: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)

    __table_args__ = (
        PrimaryKeyConstraint("tecnico_id", "cidade", "rua", name="pk_tecnico_areas"),
    )


# ════════ Ordens de Servico ════════

class OrdemServico(Base):
    __tablename__ = "ordens_servico"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    cliente_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False
    )
    tecnico_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tecnicos.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[OsStatus] = mapped_column(
        Enum(OsStatus, name="os_status", native_enum=False),
        nullable=False,
        default=OsStatus.PENDENTE,
    )
    problema: Mapped[str] = mapped_column(Text, nullable=False)
    endereco: Mapped[str] = mapped_column(Text, nullable=False)
    agendamento_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    concluida_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fotos: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    assinatura: Mapped[str | None] = mapped_column(Text, nullable=True)
    gps_inicio_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_inicio_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_fim_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_fim_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    csat: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    nps: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    comentario_cliente: Mapped[str | None] = mapped_column(Text, nullable=True)
    reatribuido_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reatribuido_por: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    historico_reatribuicoes: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    follow_up_resposta: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_respondido_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    follow_up_resultado: Mapped[str | None] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        Index("ix_os_codigo", "codigo", unique=True),
        Index("ix_os_tecnico_status", "tecnico_id", "status"),
    )


# ════════ Manutencoes ════════

class Manutencao(Base):
    __tablename__ = "manutencoes"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    inicio_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fim_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cidades: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    notificar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ════════ Notificacoes ════════

class Notificacao(Base):
    __tablename__ = "notificacoes"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    cliente_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[NotificacaoTipo] = mapped_column(
        Enum(NotificacaoTipo, name="notificacao_tipo", native_enum=False), nullable=False
    )
    agendada_para: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    enviada_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[NotificacaoStatus] = mapped_column(
        Enum(NotificacaoStatus, name="notificacao_status", native_enum=False),
        nullable=False,
        default=NotificacaoStatus.PENDENTE,
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tentativas: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_notif_status_due", "status", "agendada_para"),)


# ════════ Operacional ════════

class SgpCache(Base):
    __tablename__ = "sgp_cache"

    cpf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[SgpProvider] = mapped_column(
        Enum(SgpProvider, name="sgp_provider_cache", native_enum=False), nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ttl: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("cpf_hash", "provider", name="pk_sgp_cache"),
    )


class LlmEvalSample(Base):
    __tablename__ = "llm_eval_samples"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    conversa_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("conversas.id", ondelete="CASCADE"), nullable=False
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    reviewed_by: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Config(Base):
    __tablename__ = "config"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    updated_by: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
