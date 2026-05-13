"""Cursor-based pagination primitives for /api/v1/* list endpoints.

Cursor encoding:
- Cursor is the ISO-8601 datetime of the last item's `created_at` (or analogous time field).
- Encoded as URL-safe base64 to keep URLs clean and the format opaque to clients.
- Default limit 50, max 200.
"""
from __future__ import annotations

import base64
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def encode_cursor(ts: datetime) -> str:
    raw = ts.isoformat().encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str | None) -> datetime | None:
    if not cursor:
        return None
    try:
        pad = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode((cursor + pad).encode("ascii"))
        return datetime.fromisoformat(raw.decode("utf-8"))
    except (ValueError, TypeError):
        return None


def clamp_limit(limit: int | None) -> int:
    if limit is None or limit <= 0:
        return DEFAULT_LIMIT
    return min(limit, MAX_LIMIT)


class CursorPage(BaseModel, Generic[T]):
    """Generic cursor-paginated page."""
    items: list[T] = Field(default_factory=list)
    next_cursor: str | None = None
