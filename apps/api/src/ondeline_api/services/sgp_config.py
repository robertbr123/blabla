"""SGP credentials loader — DB-first with env fallback.

Reads `config` table keys `sgp.ondeline` and `sgp.linknetam` (admin-editable
via dashboard). Each value is `{base_url, token, app}`. Any missing field
falls back to the corresponding env var so existing deployments keep working
until the admin overrides them.
"""
from __future__ import annotations

from typing import Literal, TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.config import get_settings
from ondeline_api.repositories.config import ConfigRepo

Provider = Literal["ondeline", "linknetam"]

_CONFIG_KEYS: dict[Provider, str] = {
    "ondeline": "sgp.ondeline",
    "linknetam": "sgp.linknetam",
}


class SgpInstanceConfig(TypedDict):
    base_url: str
    token: str
    app: str


def _env_defaults(provider: Provider) -> SgpInstanceConfig:
    s = get_settings()
    if provider == "ondeline":
        return {
            "base_url": s.sgp_ondeline_base,
            "token": s.sgp_ondeline_token,
            "app": s.sgp_ondeline_app,
        }
    return {
        "base_url": s.sgp_linknetam_base,
        "token": s.sgp_linknetam_token,
        "app": s.sgp_linknetam_app,
    }


async def load_sgp_config(
    session: AsyncSession, provider: Provider
) -> SgpInstanceConfig:
    """Return SGP credentials for a provider, DB overriding env when present."""
    defaults = _env_defaults(provider)
    db_value = await ConfigRepo(session).get(_CONFIG_KEYS[provider])
    if not isinstance(db_value, dict):
        return defaults
    return {
        "base_url": str(db_value.get("base_url") or defaults["base_url"]),
        "token": str(db_value.get("token") or defaults["token"]),
        "app": str(db_value.get("app") or defaults["app"]),
    }
