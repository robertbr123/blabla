"""FastAPI dependencies for extracting the current user from access token."""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.db.models.identity import User
from ondeline_api.deps import get_db


def _bearer_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )
    return auth.removeprefix("Bearer ").strip()


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> User:
    token = _bearer_token(request)
    try:
        payload = jwt_mod.decode_access_token(token)
    except jwt_mod.TokenExpired:
        raise HTTPException(status_code=401, detail="token expired") from None
    except jwt_mod.InvalidToken as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user = await session.get(User, UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="user inactive or unknown")
    return user
