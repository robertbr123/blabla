"""Common FastAPI dependencies for the /api/v1/* router family."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import Query

from ondeline_api.api.schemas.pagination import (
    MAX_LIMIT,
    clamp_limit,
    decode_cursor,
)

CursorParam = Annotated[
    str | None,
    Query(description="Opaque cursor returned by previous page.", max_length=200),
]
LimitParam = Annotated[
    int | None,
    Query(ge=1, le=MAX_LIMIT, description=f"Page size (max {MAX_LIMIT})"),
]


def parse_cursor(cursor: str | None) -> datetime | None:
    return decode_cursor(cursor)


def parse_limit(limit: int | None) -> int:
    return clamp_limit(limit)
