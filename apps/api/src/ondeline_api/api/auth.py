"""Authentication endpoints."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.auth import lockout
from ondeline_api.auth.audit import write_audit
from ondeline_api.auth.passwords import verify_password
from ondeline_api.config import get_settings
from ondeline_api.db.models.identity import Session as DBSession
from ondeline_api.db.models.identity import User
from ondeline_api.deps import RedisLike, get_db, get_redis

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user_id: str
    role: str


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    secure = settings.cookie_secure if settings.env != "development" else False
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        path="/auth",
    )


def _set_csrf_cookie(response: Response, value: str) -> None:
    settings = get_settings()
    secure = settings.cookie_secure if settings.env != "development" else False
    response.set_cookie(
        key=CSRF_COOKIE,
        value=value,
        httponly=False,  # client le e devolve no header
        secure=secure,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
        path="/",
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),  # noqa: B008
    redis: RedisLike = Depends(get_redis),  # noqa: B008
) -> LoginResponse:
    if await lockout.is_locked(redis, payload.email):  # type: ignore[arg-type]
        await write_audit(
            session,
            user_id=None,
            action="login.locked",
            resource_type="user",
            resource_id=payload.email,
            ip=_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="too many login attempts; try again later",
        )

    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    valid = (
        user is not None
        and user.is_active
        and verify_password(payload.password, user.password_hash)
    )
    if not valid:
        state = await lockout.record_failure(redis, payload.email)  # type: ignore[arg-type]
        await write_audit(
            session,
            user_id=user.id if user else None,
            action="login.failed",
            resource_type="user",
            resource_id=payload.email,
            after={"attempts": state.attempts, "locked": state.locked},
            ip=_client_ip(request),
        )
        raise HTTPException(status_code=401, detail="invalid credentials")

    assert user is not None  # narrow for mypy
    await lockout.clear(redis, payload.email)  # type: ignore[arg-type]

    access_token = jwt_mod.encode_access_token(user.id, role=user.role.value)
    refresh_token, jti = jwt_mod.encode_refresh_token(user.id)

    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)
    db_session = DBSession(
        user_id=user.id,
        token_hash=jwt_mod.hash_refresh_token(refresh_token),
        expires_at=expires_at,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    session.add(db_session)
    user.last_login_at = datetime.now(UTC)

    await write_audit(
        session,
        user_id=user.id,
        action="login.success",
        resource_type="user",
        resource_id=str(user.id),
        ip=_client_ip(request),
    )
    await session.flush()

    _set_refresh_cookie(response, refresh_token)
    _set_csrf_cookie(response, jti)  # double-submit token

    return LoginResponse(
        access_token=access_token,
        user_id=str(user.id),
        role=user.role.value,
    )
