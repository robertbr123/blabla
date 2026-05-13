"""DTOs for Mensagem."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MensagemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    conversa_id: UUID
    role: str
    content: str | None
    media_type: str | None
    media_url: str | None
    created_at: datetime
