"""/api/v1/usuarios — gestao dos usuarios do dashboard (admin e atendente).

So admin. Tecnicos tem fluxo proprio (/api/v1/tecnicos) e nao aparecem aqui.
Para atendentes, ``cidades`` define o escopo de conversas/OS (auth/scope.py).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.usuario import UsuarioCreate, UsuarioOut, UsuarioPatch
from ondeline_api.auth.audit import write_audit
from ondeline_api.auth.passwords import hash_password
from ondeline_api.auth.rbac import require_role
from ondeline_api.auth.scope import clean_cidades, normalize_cidade
from ondeline_api.db.models.business import Cliente
from ondeline_api.db.models.identity import Role, Session, User
from ondeline_api.deps import get_db

router = APIRouter(prefix="/api/v1/usuarios", tags=["usuarios"])
_admin = require_role(Role.ADMIN)
_admin_dep = Depends(_admin)

_DASHBOARD_ROLES = (Role.ADMIN, Role.ATENDENTE)
# Mesma lista usada no cadastro de tecnico: senhas que todo mundo tenta primeiro.
_SENHAS_FRACAS = {"12345678", "123456789", "password", "senha123", "admin123", "ondeline"}


def _out(u: User) -> UsuarioOut:
    return UsuarioOut(
        id=u.id,
        email=u.email,
        name=u.name,
        role="admin" if u.role == Role.ADMIN else "atendente",
        is_active=u.is_active,
        cidades=list(u.cidades or []),
        last_login_at=u.last_login_at,
        created_at=u.created_at,
    )


def _snapshot(u: User) -> dict[str, Any]:
    """Estado pro audit_log — nunca inclui senha/hash."""
    return {
        "email": u.email,
        "name": u.name,
        "role": u.role.value,
        "is_active": u.is_active,
        "cidades": list(u.cidades or []),
    }


def _check_password(password: str) -> None:
    if password.lower() in _SENHAS_FRACAS:
        raise HTTPException(status_code=400, detail="Escolha uma senha menos óbvia.")


def _clean_email(email: str) -> str:
    e = email.strip().lower()
    if "@" not in e or "." not in e.split("@", 1)[1]:
        raise HTTPException(status_code=400, detail="Email inválido.")
    return e


async def _revoke_sessions(session: AsyncSession, user_id: UUID) -> None:
    """Derruba os refresh tokens ativos — troca de senha/desativacao vale na hora."""
    await session.execute(
        update(Session)
        .where(Session.user_id == user_id, Session.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


async def _outros_admins_ativos(session: AsyncSession, exceto: UUID) -> int:
    stmt = select(func.count(User.id)).where(
        User.role == Role.ADMIN, User.is_active.is_(True), User.id != exceto
    )
    return int((await session.execute(stmt)).scalar_one() or 0)


@router.get("", response_model=list[UsuarioOut], dependencies=[_admin_dep])
async def list_usuarios(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[UsuarioOut]:
    stmt = (
        select(User)
        .where(User.role.in_(_DASHBOARD_ROLES))
        .order_by(User.is_active.desc(), func.lower(User.name))
    )
    return [_out(u) for u in (await session.execute(stmt)).scalars().all()]


@router.get("/cidades", response_model=list[str], dependencies=[_admin_dep])
async def list_cidades(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[str]:
    """Cidades conhecidas (base de clientes) pra alimentar o seletor."""
    stmt = (
        select(Cliente.cidade, func.count(Cliente.id))
        .where(Cliente.cidade.is_not(None), Cliente.deleted_at.is_(None))
        .group_by(Cliente.cidade)
    )
    # "Ipixuna", "IPIXUNA" e " ipixuna" sao a mesma cidade: fica a grafia mais usada.
    melhor: dict[str, tuple[str, int]] = {}
    for cidade, n in (await session.execute(stmt)).all():
        nome = (cidade or "").strip()
        key = normalize_cidade(nome)
        if not key:
            continue
        if key not in melhor or n > melhor[key][1]:
            melhor[key] = (nome, int(n))
    return sorted((v[0] for v in melhor.values()), key=normalize_cidade)


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
async def create_usuario(
    body: UsuarioCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, _admin_dep],
) -> UsuarioOut:
    email = _clean_email(body.email)
    _check_password(body.password)
    existe = await session.execute(select(User.id).where(func.lower(User.email) == email))
    if existe.first() is not None:
        raise HTTPException(status_code=409, detail="Já existe um usuário com este email.")
    role = Role.ADMIN if body.role == "admin" else Role.ATENDENTE
    user = User(
        email=email,
        name=body.name.strip(),
        role=role,
        is_active=True,
        password_hash=hash_password(body.password),
        # Admin sempre ve tudo: nao guarda escopo.
        cidades=clean_cidades(body.cidades) if role == Role.ATENDENTE else None,
    )
    session.add(user)
    await session.flush()
    await write_audit(
        session,
        user_id=admin.id,
        action="usuario.create",
        resource_type="user",
        resource_id=str(user.id),
        after=_snapshot(user),
    )
    await session.refresh(user)
    return _out(user)


@router.patch("/{usuario_id}", response_model=UsuarioOut)
async def patch_usuario(
    usuario_id: UUID,
    body: UsuarioPatch,
    session: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, _admin_dep],
) -> UsuarioOut:
    user = await session.get(User, usuario_id)
    if user is None or user.role not in _DASHBOARD_ROLES:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    before = _snapshot(user)

    novo_role = user.role
    if body.role is not None:
        novo_role = Role.ADMIN if body.role == "admin" else Role.ATENDENTE
    novo_ativo = user.is_active if body.is_active is None else body.is_active

    # Travas: ninguem se tranca pra fora, e o sistema nunca fica sem admin.
    perde_admin = user.role == Role.ADMIN and (novo_role != Role.ADMIN or not novo_ativo)
    if perde_admin and user.is_active:
        if user.id == admin.id:
            raise HTTPException(
                status_code=400,
                detail="Você não pode desativar ou rebaixar o seu próprio usuário.",
            )
        if await _outros_admins_ativos(session, exceto=user.id) == 0:
            raise HTTPException(
                status_code=400,
                detail="Este é o último administrador ativo — crie outro antes.",
            )

    if body.name is not None:
        user.name = body.name.strip()
    user.role = novo_role
    user.is_active = novo_ativo
    if body.cidades is not None:
        user.cidades = clean_cidades(body.cidades)
    if user.role == Role.ADMIN:
        user.cidades = None

    senha_trocada = False
    if body.password is not None:
        _check_password(body.password)
        user.password_hash = hash_password(body.password)
        senha_trocada = True
    if senha_trocada or not user.is_active:
        await _revoke_sessions(session, user.id)

    await session.flush()
    after = _snapshot(user)
    if senha_trocada:
        after["password_reset"] = True
    await write_audit(
        session,
        user_id=admin.id,
        action="usuario.update",
        resource_type="user",
        resource_id=str(user.id),
        before=before,
        after=after,
    )
    await session.refresh(user)
    return _out(user)
