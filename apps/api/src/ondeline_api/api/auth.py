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
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.passwords import hash_password, verify_password
from ondeline_api.config import get_settings
from ondeline_api.db.models.identity import Session as DBSession
from ondeline_api.db.models.identity import User
from ondeline_api.deps import RedisLike, get_db, get_redis

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"

_DUMMY_PASSWORD_HASH: str | None = None


def _get_dummy_hash() -> str:
    """Lazily compute (or read from Settings) an argon2id hash to verify against
    when the user lookup fails. This keeps login latency for nonexistent emails
    indistinguishable from latency for wrong passwords.
    """
    global _DUMMY_PASSWORD_HASH
    if _DUMMY_PASSWORD_HASH is not None:
        return _DUMMY_PASSWORD_HASH
    settings = get_settings()
    if settings.dummy_password_hash:
        _DUMMY_PASSWORD_HASH = settings.dummy_password_hash
    else:
        # Hash a fixed-length random-ish string; never matches a real password.
        _DUMMY_PASSWORD_HASH = hash_password("__timing_oracle_dummy__")
    return _DUMMY_PASSWORD_HASH


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

    # Always call verify_password — against the real hash if user is found and active,
    # otherwise against the dummy hash. Constant-time behavior prevents email enumeration.
    if user is not None and user.is_active:
        password_hash = user.password_hash
    else:
        password_hash = _get_dummy_hash()

    password_ok = verify_password(payload.password, password_hash)
    valid = user is not None and user.is_active and password_ok

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


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> RefreshResponse:
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="missing refresh token")
    try:
        jwt_mod.decode_refresh_token(raw)
    except jwt_mod.InvalidToken as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    token_hash = jwt_mod.hash_refresh_token(raw)
    res = await session.execute(
        select(DBSession).where(DBSession.token_hash == token_hash)
    )
    db_session_row = res.scalar_one_or_none()
    if db_session_row is None or db_session_row.revoked_at is not None:
        raise HTTPException(status_code=401, detail="session revoked or unknown")

    user = await session.get(User, db_session_row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="user inactive")

    access = jwt_mod.encode_access_token(user.id, role=user.role.value)
    return RefreshResponse(access_token=access)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> Response:
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        token_hash = jwt_mod.hash_refresh_token(raw)
        res = await session.execute(
            select(DBSession).where(DBSession.token_hash == token_hash)
        )
        db_session_row = res.scalar_one_or_none()
        if db_session_row and db_session_row.revoked_at is None:
            db_session_row.revoked_at = datetime.now(UTC)
            await write_audit(
                session,
                user_id=db_session_row.user_id,
                action="logout",
                resource_type="session",
                resource_id=str(db_session_row.id),
                ip=_client_ip(request),
            )
            await session.flush()

    response.delete_cookie(REFRESH_COOKIE, path="/auth")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return Response(status_code=204)


class MeResponse(BaseModel):
    user_id: str
    email: str
    name: str
    role: str
    is_active: bool


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user)) -> MeResponse:  # noqa: B008
    return MeResponse(
        user_id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role.value,
        is_active=user.is_active,
    )
