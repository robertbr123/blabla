"""F6 — Modelos de estoque do técnico."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from ondeline_api.db.base import Base


class ItemCategoria(StrEnum):
    ONU = "onu"
    ROTEADOR = "roteador"
    CABO = "cabo"
    CONECTOR = "conector"
    OUTRO = "outro"


class MovimentoTipo(StrEnum):
    """Sinal aplicado ao saldo do técnico:

    entrada / recolhido / ajuste_positivo → +quantidade
    saida / devolucao / perda / ajuste_negativo → -quantidade
    """

    ENTRADA = "entrada"          # almoxarifado → técnico
    SAIDA = "saida"              # técnico → cliente (instalação)
    RECOLHIDO = "recolhido"      # cliente → técnico (troca / retirada)
    DEVOLUCAO = "devolucao"      # técnico → almoxarifado
    PERDA = "perda"              # baixa sem destino
    AJUSTE_POSITIVO = "ajuste_positivo"
    AJUSTE_NEGATIVO = "ajuste_negativo"


# Tipos que aumentam o saldo do técnico (signal +1).
TIPOS_POSITIVOS: frozenset[str] = frozenset(
    {
        MovimentoTipo.ENTRADA.value,
        MovimentoTipo.RECOLHIDO.value,
        MovimentoTipo.AJUSTE_POSITIVO.value,
    }
)


class EstoqueItem(Base):
    __tablename__ = "estoque_item"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    sku: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    categoria: Mapped[str] = mapped_column(String(20), nullable=False)
    serializado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    ativo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ClienteEquipamento(Base):
    """F8 — Rastreio de equipamento serializado instalado em cliente.

    Linha criada quando técnico faz `saida` com `ordem_servico_id` (item
    serializado, com serial). Fechada (removido_em preenchido) quando o mesmo
    serial é registrado como `recolhido`.
    """

    __tablename__ = "cliente_equipamento"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    cliente_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("estoque_item.id", ondelete="RESTRICT"),
        nullable=False,
    )
    serial: Mapped[str] = mapped_column(String(120), nullable=False)
    instalado_em_os_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("ordens_servico.id", ondelete="SET NULL"),
        nullable=True,
    )
    instalado_por_tecnico_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tecnicos.id", ondelete="SET NULL"),
        nullable=True,
    )
    instalado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    removido_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    removido_em_os_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("ordens_servico.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        Index(
            "ix_cliente_equipamento_cliente", "cliente_id", "instalado_em"
        ),
    )


class EstoqueMovimento(Base):
    __tablename__ = "estoque_movimento"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    item_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("estoque_item.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tecnico_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tecnicos.id", ondelete="RESTRICT"),
        nullable=True,
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    serial: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ordem_servico_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("ordens_servico.id", ondelete="SET NULL"),
        nullable=True,
    )
    cliente_cadastro_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clientes_cadastro.id", ondelete="SET NULL"),
        nullable=True,
    )
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_por: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_estoque_quantidade_positiva"),
        CheckConstraint(
            "tipo IN ('entrada','saida','devolucao','perda',"
            "'ajuste_positivo','ajuste_negativo','recolhido')",
            name="ck_estoque_tipo_enum",
        ),
        Index("ix_estoque_mov_tecnico_item", "tecnico_id", "item_id"),
        Index("ix_estoque_mov_os", "ordem_servico_id"),
        Index("ix_estoque_mov_cliente_cadastro", "cliente_cadastro_id"),
    )
