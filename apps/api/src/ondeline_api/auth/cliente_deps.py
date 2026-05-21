"""FastAPI deps para usuario do app cliente."""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.deps import get_db


def _bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )
    return auth.removeprefix("Bearer ").strip()


async def get_current_cliente_user(
    request: Request,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> ClienteAppUser:
    token = _bearer(request)
    try:
        payload = jwt_mod.decode_cliente_access_token(token)
    except jwt_mod.TokenExpired:
        raise HTTPException(status_code=401, detail="token expired") from None
    except jwt_mod.InvalidTokenKind:
        raise HTTPException(status_code=401, detail="invalid token kind") from None
    except jwt_mod.InvalidToken as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user = await session.get(ClienteAppUser, UUID(payload["sub"]))
    if user is None or user.status != "active":
        raise HTTPException(status_code=401, detail="user inactive or unknown")
    return user
