"""Root conftest: set required env vars before collection so module-level
imports (e.g. celery_app = create_celery_app()) succeed without validation
errors from pydantic-settings.
"""
from __future__ import annotations

import os


def pytest_configure(config) -> None:  # type: ignore[no-untyped-def]
    """Called early — before collection — so module-level imports that read
    settings (like the celery_app factory) don't fail with missing-field errors.
    All values here are test-only; production reads from real env / .env file.
    """
    from cryptography.fernet import Fernet

    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://ondeline:ondeline@localhost:5433/ondeline",
    )
    os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")
    os.environ.setdefault("JWT_SECRET", "test-jwt-secret-32-bytes-minimum-okk")
    os.environ.setdefault("PII_ENCRYPTION_KEY", Fernet.generate_key().decode())
    os.environ.setdefault("PII_HASH_PEPPER", "test-pepper-not-for-prod-32-bytes-x")
