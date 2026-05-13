"""Sentry SDK initialization (no-op when DSN is empty)."""
from __future__ import annotations

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.types import Event, Hint

from ondeline_api.config import get_settings
from ondeline_api.services.pii_mask import mask_pii


def _before_send(event: Event, _hint: Hint) -> Event | None:
    """Apply mask_pii to message and breadcrumb messages before they leave the process."""
    if msg := event.get("message"):
        if isinstance(msg, str):
            event["message"] = mask_pii(msg)
    breadcrumbs = event.get("breadcrumbs")
    if isinstance(breadcrumbs, dict):
        for crumb in breadcrumbs.get("values", []) or []:
            if isinstance(crumb.get("message"), str):
                crumb["message"] = mask_pii(crumb["message"])
    return event


_INITIALIZED = False


def init_sentry(*, component: str) -> bool:
    """Initialize Sentry. Returns True if init ran, False if no-op.

    `component` is one of: "api" | "worker" | "beat". Used in tags.
    """
    global _INITIALIZED
    if _INITIALIZED:
        return False
    settings = get_settings()
    if not settings.sentry_dsn:
        return False
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.env,
        traces_sample_rate=0.0,  # OTel handles traces; Sentry só pega erros
        send_default_pii=False,
        before_send=_before_send,
        integrations=[
            FastApiIntegration(),
            StarletteIntegration(),
            CeleryIntegration(),
            SqlalchemyIntegration(),
        ],
    )
    sentry_sdk.set_tag("component", component)
    _INITIALIZED = True
    return True
