"""ORM models para o app do cliente final."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ondeline_api.db.base import Base


class ClienteAppUser(Base):
    __tablename__ = "cliente_app_users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cpf_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    cpf_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    cpf_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    nome_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    telefone_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    email_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    sgp_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    push_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    biometric_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending_otp")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ClienteAppOs(Base):
    __tablename__ = "cliente_app_os"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_app_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(24), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False, default="")
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="aberto")
    sgp_protocolo_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    atendente_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ClienteAppOtp(Base):
    __tablename__ = "cliente_app_otp"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cpf_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
