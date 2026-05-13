"""DTOs for Config k/v."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key: str
    value: Any
    updated_by: UUID | None
    updated_at: datetime


class ConfigSet(BaseModel):
    value: Any
