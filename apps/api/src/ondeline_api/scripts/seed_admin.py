"""Idempotent seed of an initial admin user.

Reads ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_NAME from env. If a user with that email
already exists, update name and ensure role=ADMIN and is_active=True (without
touching password). Otherwise insert a new ADMIN user.

Run via: python -m ondeline_api.scripts.seed_admin
"""
from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.passwords import hash_password
from ondeline_api.db.engine import get_sessionmaker
from ondeline_api.db.models.identity import Role, User


async def _seed(session: AsyncSession, *, email: str, password: str, name: str) -> str:
    result = await session.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing is not None:
        existing.role = Role.ADMIN
        existing.is_active = True
        existing.name = name
        await session.flush()
        return f"updated existing user id={existing.id} email={email}"
    user = User(
        email=email,
        name=name,
        role=Role.ADMIN,
        is_active=True,
        password_hash=hash_password(password),
    )
    session.add(user)
    await session.flush()
    return f"created admin user id={user.id} email={email}"


async def _main() -> int:
    email = os.environ.get("ADMIN_EMAIL", "").strip()
    password = os.environ.get("ADMIN_PASSWORD", "")
    name = os.environ.get("ADMIN_NAME", "Admin").strip() or "Admin"
    if not email or "@" not in email:
        print("ERROR: set ADMIN_EMAIL to a valid address", file=sys.stderr)
        return 2
    if len(password) < 12 or password.lower() in {"password", "admin1234567", "changeme1234"}:
        print(
            "ERROR: ADMIN_PASSWORD must be >= 12 chars and not a default placeholder",
            file=sys.stderr,
        )
        return 2

    factory = get_sessionmaker()
    async with factory() as session:
        try:
            msg = await _seed(session, email=email, password=password, name=name)
            await session.commit()
            print(msg)
            return 0
        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
