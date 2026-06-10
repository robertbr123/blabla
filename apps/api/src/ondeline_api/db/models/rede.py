"""ORM model para auditoria de troca de senha WiFi (TR-069).

Registra o FATO da troca (quem, qual ONU, quando) - NUNCA a senha em si.
A identificacao do cliente e por cpf_hash (PII-safe): o cliente e localizado
por CPF -> SGP -> pppoe, entao nem sempre existe um id de cliente local.
Status comeca em 'enviado'; fatias futuras (app cliente) podem evoluir
para 'confirmado'/'falhou'.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ondeline_api.db.base import Base


class RedeWifiPedido(Base):
    __tablename__ = "rede_wifi_pedido"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # cpf_hash (HMAC) e a chave de cliente PII-safe; cliente_id local e opcional.
    cpf_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    contrato_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pppoe_login: Mapped[str | None] = mapped_column(String(128), nullable=True)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ator_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="enviado")
    reiniciou: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
