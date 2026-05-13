"""Global structlog configuration with PII masking processor.

Provides a single `configure_logging()` entry point used by both the FastAPI
startup (via `create_app()`) and Celery workers (via `worker_process_init`).

In production: JSONRenderer + PII mask applied recursively to all event values.
In development: ConsoleRenderer (colored). Level is driven by Settings.log_level.
"""
from __future__ import annotations

import logging
from typing import Any

import structlog

from ondeline_api.config import get_settings
from ondeline_api.services.pii_mask import mask_pii


def _walk(value: Any) -> Any:
    """Recursively apply mask_pii() to all string values in a nested structure."""
    if isinstance(value, str):
        return mask_pii(value)
    if isinstance(value, dict):
        return {k: _walk(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_walk(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_walk(v) for v in value)
    return value


def _mask_pii_processor(
    _logger: Any, _method: str, event_dict: structlog.types.EventDict
) -> structlog.types.EventDict:
    """Structlog processor that masks PII in every string value of the event dict."""
    masked = _walk(dict(event_dict))
    assert isinstance(masked, dict)
    return masked


_CONFIGURED = False


def configure_logging() -> None:
    """Configure structlog globally. Idempotent — safe to call multiple times."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _mask_pii_processor,
    ]
    if settings.env == "development":
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True
