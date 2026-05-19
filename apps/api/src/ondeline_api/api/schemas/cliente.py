"""DTOs for Cliente. List view masks PII; detail view decrypts."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClienteListItem(BaseModel):
    """List view — nome decifrado (admin/atendente já tem acesso) pra facilitar identificação."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    whatsapp: str
    nome: str | None = None  # decifrado server-side
    plano: str | None
    status: str | None
    cidade: str | None
    sgp_provider: str | None
    sgp_id: str | None
    created_at: datetime
    last_seen_at: datetime | None


class ClienteDetail(ClienteListItem):
    """Detail view — PII decrypted server-side."""
    nome: str
    cpf_cnpj: str
    endereco: str | None
    retention_until: datetime | None
