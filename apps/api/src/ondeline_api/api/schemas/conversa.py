"""DTOs for Conversa."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ondeline_api.api.schemas.mensagem import MensagemOut


class ClienteEmbutido(BaseModel):
    id: UUID
    nome: str
    cpf_cnpj: str
    whatsapp: str
    plano: str | None
    cidade: str | None
    endereco: str | None


class ConversaListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    whatsapp: str
    estado: str
    status: str
    cliente_id: UUID | None
    atendente_id: UUID | None
    created_at: datetime
    last_message_at: datetime | None
    transferred_at: datetime | None = None
    first_response_at: datetime | None = None
    tags: list[str] | None = None
    sla_minutes: int = 15


class ConversaOut(ConversaListItem):
    mensagens: list[MensagemOut] = Field(default_factory=list)
    cliente: ClienteEmbutido | None = None


class ResponderIn(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
