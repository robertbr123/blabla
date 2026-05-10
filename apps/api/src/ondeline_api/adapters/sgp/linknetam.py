"""SgpLinkNetAMProvider — mesmo shape do Ondeline, base + token diferentes."""
from __future__ import annotations

from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum


class SgpLinkNetAMProvider(SgpOndelineProvider):
    name = SgpProviderEnum.LINKNETAM
