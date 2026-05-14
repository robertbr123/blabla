"""Service layer for managing a Tecnico's linked login User.

Encapsulates the User row that backs a Tecnico's PWA login: creating it,
resetting its password, and toggling its active flag. Centralised here so
the password/email rules match seed_admin (length, simple blocklist) and
so the API endpoints stay thin.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.passwords import hash_password
from ondeline_api.db.models.business import Tecnico
from ondeline_api.db.models.identity import Role, User

_PASSWORD_BLOCKLIST = {"password", "12345678", "admin1234", "changeme"}


class TecnicoUserError(ValueError):
    """Raised when input fails validation (caught by API → 400)."""


def _validate_email(email: str) -> str:
    e = email.strip()
    if not e or "@" not in e or "." not in e.split("@", 1)[1]:
        raise TecnicoUserError("email inválido")
    return e


def _validate_password(password: str) -> str:
    if len(password) < 8 or password.lower() in _PASSWORD_BLOCKLIST:
        raise TecnicoUserError(
            "senha precisa ter 8+ caracteres e não pode ser uma senha padrão"
        )
    return password


async def _email_in_use(session: AsyncSession, email: str, *, exclude_id: str | None = None) -> bool:
    stmt = select(User.id).where(User.email == email)
    rows = (await session.execute(stmt)).scalars().all()
    if exclude_id is None:
        return bool(rows)
    return any(str(r) != exclude_id for r in rows)


async def create_user_for_tecnico(
    session: AsyncSession,
    tec: Tecnico,
    *,
    email: str,
    password: str,
    name: str | None = None,
) -> User:
    """Create a User (role=tecnico) and link it to the given Tecnico.

    Raises TecnicoUserError on invalid input or email-already-in-use.
    Raises ValueError if the tecnico is already linked to a user.
    """
    if tec.user_id is not None:
        raise TecnicoUserError("técnico já tem acesso de login criado")
    e = _validate_email(email)
    p = _validate_password(password)
    if await _email_in_use(session, e):
        raise TecnicoUserError("email já está em uso")
    user = User(
        email=e,
        name=name or tec.nome,
        role=Role.TECNICO,
        is_active=True,
        password_hash=hash_password(p),
    )
    session.add(user)
    await session.flush()
    tec.user_id = user.id
    await session.flush()
    return user


async def reset_user_password(
    session: AsyncSession, user: User, *, new_password: str
) -> None:
    p = _validate_password(new_password)
    user.password_hash = hash_password(p)
    await session.flush()


async def set_user_active(session: AsyncSession, user: User, *, active: bool) -> None:
    user.is_active = active
    await session.flush()
