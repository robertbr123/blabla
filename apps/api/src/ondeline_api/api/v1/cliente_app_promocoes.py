"""Routers de promoções.

- `/api/v1/cliente-app/promocoes` — cliente lista promoções ativas pro proprio segmento.
- `/api/v1/admin/promocoes` — admin CRUD + reorder + upload imagem + metricas.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

if TYPE_CHECKING:
    from ondeline_api.adapters.sgp.base import ClienteSgp

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import asc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.promocao import (
    PromocaoAdminOut,
    PromocaoCreateIn,
    PromocaoEventoIn,
    PromocaoEventoOut,
    PromocaoOut,
    PromocaoReorderIn,
    PromocaoUpdateIn,
)
from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.db.models.identity import Role, User
from ondeline_api.db.models.promocoes import Promocao, PromocaoEvento
from ondeline_api.deps import get_db

log = structlog.get_logger(__name__)

# Diretorio dos uploads de imagem. Servido em /static/promocoes/.
# /tmp tem perm liberada no startup (lifespan) + e mapeavel como volume.
STATIC_DIR = Path("/tmp/ondeline_promocoes")
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_BYTES = 2 * 1024 * 1024  # 2 MB

# ════════════════════════ Cliente router ════════════════════════

router = APIRouter(prefix="/api/v1/cliente-app/promocoes", tags=["cliente-app:promocoes"])


def _promo_out(p: Promocao) -> PromocaoOut:
    return PromocaoOut(
        id=p.id,
        titulo=p.titulo,
        subtitulo=p.subtitulo,
        imagem_url=p.imagem_url,
        cta_label=p.cta_label,
        cta_action=p.cta_action,
        tipo=p.tipo,
        ativa=p.ativa,
        ordem=p.ordem,
        valido_de=p.valido_de,
        valido_ate=p.valido_ate,
        segmento=p.segmento,
        gradient_from=p.gradient_from,
        gradient_to=p.gradient_to,
        icon=p.icon,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _segmento_aplicavel(segmento: str, cliente_sgp: ClienteSgp | None) -> bool:
    """Filtro de segmentacao baseado no estado SGP do cliente.

    Valores suportados:
    - ``todos`` — todo mundo ve.
    - ``inadimplentes`` — algum titulo aberto com ``dias_atraso > 0``.
    - ``adimplentes`` — nenhum titulo aberto em atraso.
    - ``plano:<plano>`` — algum contrato cujo nome do plano bata.

    Conservador: se nao foi possivel carregar o SGP (cliente_sgp=None),
    qualquer segmento != ``todos`` esconde a promo.
    """
    if segmento == "todos":
        return True
    if cliente_sgp is None:
        return False
    if segmento == "inadimplentes":
        return any(
            t.status == "aberto" and (t.dias_atraso or 0) > 0
            for t in cliente_sgp.titulos
        )
    if segmento == "adimplentes":
        return not any(
            t.status == "aberto" and (t.dias_atraso or 0) > 0
            for t in cliente_sgp.titulos
        )
    if segmento.startswith("plano:"):
        plano = segmento[len("plano:"):]
        return any(c.plano == plano for c in cliente_sgp.contratos)
    return False


async def _load_sgp_for_user(
    session: AsyncSession, user: ClienteAppUser
) -> ClienteSgp | None:
    """Carrega ClienteSgp do user via cache. Imports inline pra leveza.

    Mesma estrategia de ``cliente_app_auth._sgp_lookup_by_cpf`` — vale
    extrair pra service compartilhada num refactor futuro.
    """
    from ondeline_api.adapters.sgp.linknetam import SgpLinkNetAMProvider
    from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider
    from ondeline_api.adapters.sgp.router import SgpRouter
    from ondeline_api.config import get_settings
    from ondeline_api.db.crypto import decrypt_pii
    from ondeline_api.services.sgp_cache import SgpCacheService
    from ondeline_api.services.sgp_config import load_sgp_config
    from ondeline_api.workers.runtime import get_redis

    try:
        cpf = decrypt_pii(user.cpf_encrypted)
    except Exception:
        return None
    s = get_settings()
    redis = await get_redis()
    sgp_ond = await load_sgp_config(session, "ondeline")
    sgp_lnk = await load_sgp_config(session, "linknetam")
    router_sgp = SgpRouter(
        primary=SgpOndelineProvider(**sgp_ond),
        secondary=SgpLinkNetAMProvider(**sgp_lnk),
    )
    cache = SgpCacheService(
        redis=redis,
        session=session,
        router=router_sgp,
        ttl_cliente=s.sgp_cache_ttl_cliente,
        ttl_negativo=s.sgp_cache_ttl_negativo,
    )
    return await cache.get_cliente(cpf)


@router.get("", response_model=list[PromocaoOut])
async def listar_para_cliente(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[PromocaoOut]:
    now = datetime.now(tz=UTC)
    stmt = (
        select(Promocao)
        .where(Promocao.ativa.is_(True))
        .order_by(asc(Promocao.ordem), asc(Promocao.created_at))
    )
    rows = list((await session.execute(stmt)).scalars())

    # Pre-carrega SGP UMA vez SE alguma promo ativa tem segmento != 'todos'.
    # Tudo cai num cache de 1h (sgp_cache_ttl_cliente), entao a chamada e
    # barata em quase toda request.
    needs_sgp = any(
        p.segmento != "todos"
        for p in rows
        if (p.valido_de is None or p.valido_de <= now)
        and (p.valido_ate is None or p.valido_ate >= now)
    )
    cliente_sgp = await _load_sgp_for_user(session, user) if needs_sgp else None

    out: list[PromocaoOut] = []
    for p in rows:
        if p.valido_de is not None and p.valido_de > now:
            continue
        if p.valido_ate is not None and p.valido_ate < now:
            continue
        if not _segmento_aplicavel(p.segmento, cliente_sgp):
            continue
        out.append(_promo_out(p))
    return out


@router.post("/{promo_id}/evento", response_model=PromocaoEventoOut)
async def registrar_evento(
    promo_id: UUID,
    body: PromocaoEventoIn,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PromocaoEventoOut:
    promo = await session.get(Promocao, promo_id)
    if promo is None:
        raise HTTPException(status_code=404, detail="promocao nao encontrada")
    ev = PromocaoEvento(
        promocao_id=promo_id,
        cliente_app_user_id=user.id,
        tipo=body.tipo,
    )
    session.add(ev)
    await session.commit()
    return PromocaoEventoOut(ok=True)


# ════════════════════════ Admin router ════════════════════════

admin_router = APIRouter(
    prefix="/api/v1/admin/promocoes",
    tags=["admin:promocoes"],
)


async def _stats(session: AsyncSession, promo_id: UUID) -> tuple[int, int]:
    rows = (
        await session.execute(
            select(PromocaoEvento.tipo, func.count())
            .where(PromocaoEvento.promocao_id == promo_id)
            .group_by(PromocaoEvento.tipo)
        )
    ).all()
    by = {t: int(c) for t, c in rows}
    return by.get("view", 0), by.get("click", 0)


def _admin_out(p: Promocao, views: int, clicks: int) -> PromocaoAdminOut:
    base = _promo_out(p)
    ctr = (clicks / views * 100.0) if views > 0 else 0.0
    return PromocaoAdminOut(
        **base.model_dump(),
        views=views,
        clicks=clicks,
        ctr=round(ctr, 2),
    )


@admin_router.get(
    "",
    response_model=list[PromocaoAdminOut],
    dependencies=[Depends(require_role(Role.ATENDENTE, Role.ADMIN))],
)
async def admin_listar(
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[PromocaoAdminOut]:
    stmt = select(Promocao).order_by(asc(Promocao.ordem), asc(Promocao.created_at))
    rows = list((await session.execute(stmt)).scalars())
    out: list[PromocaoAdminOut] = []
    for p in rows:
        v, c = await _stats(session, p.id)
        out.append(_admin_out(p, v, c))
    return out


@admin_router.post(
    "",
    response_model=PromocaoAdminOut,
    status_code=201,
)
async def admin_criar(
    body: PromocaoCreateIn,
    current_user: User = Depends(require_role(Role.ADMIN)),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PromocaoAdminOut:
    from ondeline_api.services.cliente_app_notif import broadcast

    promo = Promocao(
        **body.model_dump(),
        created_by=current_user.id,
    )
    session.add(promo)
    await session.flush()
    # Broadcast pra todos os clientes ativos quando promo nasce ativa.
    if promo.ativa:
        await broadcast(
            session,
            "promocao",
            promo.titulo,
            promo.subtitulo,
            action="tela:/home",
            payload={"promocao_id": str(promo.id)},
        )
    await session.commit()
    await session.refresh(promo)
    return _admin_out(promo, 0, 0)


@admin_router.get(
    "/{promo_id}",
    response_model=PromocaoAdminOut,
    dependencies=[Depends(require_role(Role.ATENDENTE, Role.ADMIN))],
)
async def admin_detalhe(
    promo_id: UUID,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PromocaoAdminOut:
    p = await session.get(Promocao, promo_id)
    if p is None:
        raise HTTPException(status_code=404, detail="promocao nao encontrada")
    v, c = await _stats(session, p.id)
    return _admin_out(p, v, c)


@admin_router.patch(
    "/{promo_id}",
    response_model=PromocaoAdminOut,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_atualizar(
    promo_id: UUID,
    body: PromocaoUpdateIn,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PromocaoAdminOut:
    from ondeline_api.services.cliente_app_notif import broadcast

    p = await session.get(Promocao, promo_id)
    if p is None:
        raise HTTPException(status_code=404, detail="promocao nao encontrada")
    ativa_antes = p.ativa
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(p, k, v)
    await session.flush()
    # Broadcast se acabou de ser ativada.
    if not ativa_antes and p.ativa:
        await broadcast(
            session,
            "promocao",
            p.titulo,
            p.subtitulo,
            action="tela:/home",
            payload={"promocao_id": str(p.id)},
        )
    await session.commit()
    await session.refresh(p)
    views, clicks = await _stats(session, p.id)
    return _admin_out(p, views, clicks)


@admin_router.delete(
    "/{promo_id}",
    status_code=204,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_remover(
    promo_id: UUID,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    p = await session.get(Promocao, promo_id)
    if p is None:
        raise HTTPException(status_code=404, detail="promocao nao encontrada")
    # Remove imagem fisica se houver e for nosso static
    if p.imagem_url and p.imagem_url.startswith("/static/promocoes/"):
        fname = Path(p.imagem_url).name
        f = STATIC_DIR / fname
        if f.exists():
            try:
                f.unlink()
            except OSError:
                pass
    await session.delete(p)
    await session.commit()


@admin_router.post(
    "/reorder",
    response_model=list[PromocaoAdminOut],
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_reorder(
    body: PromocaoReorderIn,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[PromocaoAdminOut]:
    for idx, pid in enumerate(body.ids):
        p = await session.get(Promocao, pid)
        if p is None:
            continue
        p.ordem = idx
    await session.commit()
    return await admin_listar(session=session)


@admin_router.post(
    "/{promo_id}/imagem",
    response_model=PromocaoAdminOut,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_upload_imagem(
    promo_id: UUID,
    file: Annotated[UploadFile, File()],
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PromocaoAdminOut:
    p = await session.get(Promocao, promo_id)
    if p is None:
        raise HTTPException(status_code=404, detail="promocao nao encontrada")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXT:
        raise HTTPException(
            status_code=415,
            detail=f"tipo invalido (use: {sorted(ALLOWED_EXT)})",
        )

    fname = f"{uuid.uuid4().hex}{suffix}"
    fpath = STATIC_DIR / fname
    bytes_written = 0
    with fpath.open("wb") as out:
        while chunk := await file.read(1024 * 64):
            bytes_written += len(chunk)
            if bytes_written > MAX_BYTES:
                out.close()
                fpath.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="imagem maior que 2MB")
            out.write(chunk)

    # Remove imagem antiga se for nosso static
    if p.imagem_url and p.imagem_url.startswith("/static/promocoes/"):
        old = STATIC_DIR / Path(p.imagem_url).name
        if old.exists() and old.name != fname:
            try:
                old.unlink()
            except OSError:
                pass

    p.imagem_url = f"/static/promocoes/{fname}"
    await session.commit()
    await session.refresh(p)
    v, c = await _stats(session, p.id)
    return _admin_out(p, v, c)


# ════════════════════════ Templates ════════════════════════

# Lista de promocoes-modelo prontas pra Robert apenas editar.
# Todas criadas inativas, pra ele revisar e ativar quando quiser.
_TEMPLATES: list[dict[str, object]] = [
    {
        "titulo": "Upgrade pra 1 Giga",
        "subtitulo": "Velocidade dobrada com o mesmo valor no primeiro mes.",
        "cta_label": "Quero esse",
        "cta_action": "tela:/suporte/novo",
        "tipo": "generica",
        "ativa": False,
        "ordem": 100,
        "segmento": "todos",
        "gradient_from": "#8B5CF6",
        "gradient_to": "#5B6CFF",
        "icon": "rocket_launch_rounded",
    },
    {
        "titulo": "Indique e ganhe R$30",
        "subtitulo": "Desconto na sua proxima fatura por indicacao convertida.",
        "cta_label": "Indicar agora",
        # tipo indicacao forca cta_action='tela:/indicacao' no validator
        "tipo": "indicacao",
        "ativa": False,
        "ordem": 101,
        "segmento": "todos",
        "gradient_from": "#E0455A",
        "gradient_to": "#E8A33D",
        "icon": "card_giftcard_rounded",
    },
    {
        "titulo": "Aplicativo de seguranca gratis",
        "subtitulo": "Antivirus pro celular incluso pra clientes Ondeline.",
        "cta_label": "Ativar",
        "cta_action": "info",
        "tipo": "generica",
        "ativa": False,
        "ordem": 102,
        "segmento": "todos",
        "gradient_from": "#14B8B0",
        "gradient_to": "#0F8F89",
        "icon": "shield_rounded",
    },
    {
        "titulo": "Manutencao programada na sua regiao",
        "subtitulo": "Confira datas e horarios pra nao ser pego de surpresa.",
        "cta_label": "Ver detalhes",
        "cta_action": "info",
        "tipo": "generica",
        "ativa": False,
        "ordem": 103,
        "segmento": "todos",
        "gradient_from": "#F59E0B",
        "gradient_to": "#DC2626",
        "icon": "home_repair_service_rounded",
    },
    {
        "titulo": "App do banco com Pix mais rapido",
        "subtitulo": "Pague suas faturas escaneando o QR direto pelo aplicativo.",
        "cta_label": "Como pagar",
        "cta_action": "info",
        "tipo": "generica",
        "ativa": False,
        "ordem": 104,
        "segmento": "todos",
        "gradient_from": "#0EA5E9",
        "gradient_to": "#1E40AF",
        "icon": "payments_rounded",
    },
]


@admin_router.post(
    "/seed-templates",
    response_model=list[PromocaoAdminOut],
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_seed_templates(
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[PromocaoAdminOut]:
    """Cria promocoes-modelo (inativas) pro admin editar e ativar.

    Idempotente: so insere se ainda nao existe promo com mesmo titulo.
    Retorna a lista atual ordenada (template + existentes).
    """
    inserted: list[Promocao] = []
    for tpl in _TEMPLATES:
        existing = (
            await session.execute(
                select(Promocao).where(Promocao.titulo == tpl["titulo"]).limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue
        # CTA do tipo indicacao e sobreescrito pelo schema validator,
        # entao aqui basta passar os campos validados.
        promo = Promocao(**tpl)
        session.add(promo)
        inserted.append(promo)
    await session.commit()
    log.info("promocoes.seed_templates", inseridas=len(inserted))
    # Retorna a lista completa atual
    return await admin_listar(session=session)
