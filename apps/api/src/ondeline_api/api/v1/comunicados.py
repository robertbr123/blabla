# apps/api/src/ondeline_api/api/v1/comunicados.py
"""POST/GET /api/v1/admin/comunicados — campanhas de disparo em massa + export."""
from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.whatsapp import WhatsAppError, build_for_canal
from ondeline_api.api.schemas.comunicado import (
    BroadcastTemplateOut,
    CampanhaCreate,
    CampanhaDetail,
    CampanhaListItem,
    ImportResult,
    PreviewOut,
    SegmentoFiltros,
    SegmentoValores,
    SyncResult,
    TemplateUpsert,
    TestSendIn,
)
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.config import get_settings
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import (
    BroadcastTemplate,
    Campanha,
    CampanhaDestinatario,
    Canal,
    Cliente,
)
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.repositories.campanha import CampanhaRepo
from ondeline_api.services.broadcast_import import parse_csv_destinatarios
from ondeline_api.services.segmento import (
    amostra_segmento,
    contar_segmento,
    resolver_segmento,
    valores_distintos,
)
from ondeline_api.services.whatsapp_templates_sync import sincronizar_templates
from ondeline_api.workers.broadcast import send_campanha_task

router = APIRouter(prefix="/api/v1/admin/comunicados", tags=["comunicados"])
_admin_dep = Depends(require_role(Role.ADMIN))


def _to_list_item(c: Campanha) -> CampanhaListItem:
    return CampanhaListItem(
        id=c.id, titulo=c.titulo, template_name=c.template_name, status=c.status,
        total_destinatarios=c.total_destinatarios, enviadas=c.enviadas,
        falhas=c.falhas, created_at=c.created_at,
    )


@router.get("/templates", dependencies=[_admin_dep])
async def list_templates(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[BroadcastTemplateOut]:
    stmt = select(BroadcastTemplate).where(BroadcastTemplate.ativo.is_(True))
    rows = list((await session.execute(stmt)).scalars().all())
    # model_validate(from_attributes) coage variaveis (list[dict] do JSONB) em
    # list[TemplateVar] — evita erro do plugin mypy do pydantic.
    return [BroadcastTemplateOut.model_validate(t, from_attributes=True) for t in rows]


@router.get("", dependencies=[_admin_dep])
async def list_campanhas(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[CampanhaListItem]:
    repo = CampanhaRepo(session)
    return [_to_list_item(c) for c in await repo.list_all()]


@router.post("", status_code=201, dependencies=[_admin_dep])
async def create_campanha(
    body: CampanhaCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> CampanhaListItem:
    canal = (
        await session.execute(select(Canal).where(Canal.id == body.canal_id))
    ).scalar_one_or_none()
    if canal is None:
        raise HTTPException(status_code=404, detail="canal não encontrado")
    if canal.provider != "cloud":
        raise HTTPException(
            status_code=400, detail="disparo em massa exige canal Cloud (Meta)"
        )
    camp = Campanha(
        titulo=body.titulo, canal_id=body.canal_id, template_name=body.template_name,
        template_language=body.template_language, body_params=body.body_params,
        header_media_url=body.header_media_url,
        segmentacao=body.segmentacao.model_dump(exclude_none=True),
        status="rascunho", created_by=user.id,
        origem=body.origem,
        button_param=body.button_param,
    )
    session.add(camp)
    await session.commit()
    await session.refresh(camp)
    return _to_list_item(camp)


@router.post("/preview", dependencies=[_admin_dep])
async def preview(
    filtros: SegmentoFiltros,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PreviewOut:
    f = filtros.model_dump(exclude_none=True)
    total = await contar_segmento(session, f)
    amostra = await amostra_segmento(session, f, limite=10)
    return PreviewOut(total=total, amostra=amostra)


@router.get("/export/clientes", dependencies=[_admin_dep])
async def export_clientes(
    session: Annotated[AsyncSession, Depends(get_db)],
    cidade: Annotated[str | None, Query()] = None,
    status_f: Annotated[str | None, Query(alias="status")] = None,
    plano: Annotated[str | None, Query()] = None,
    fmt: Annotated[str, Query(alias="format")] = "csv",
) -> StreamingResponse:
    filtros: dict[str, Any] = {"cidade": cidade, "status": status_f, "plano": plano}
    stmt = resolver_segmento(filtros).order_by(Cliente.created_at.desc())
    clientes = list((await session.execute(stmt)).scalars().all())

    colunas = ["nome", "cpf_cnpj", "whatsapp", "cidade", "plano", "status", "sgp_id"]

    def _row(c: Cliente) -> dict[str, str]:
        try:
            nome = decrypt_pii(c.nome_encrypted) if c.nome_encrypted else ""
        except Exception:
            nome = ""
        try:
            cpf = decrypt_pii(c.cpf_cnpj_encrypted) if c.cpf_cnpj_encrypted else ""
        except Exception:
            cpf = ""
        return {
            "nome": nome, "cpf_cnpj": cpf, "whatsapp": c.whatsapp,
            "cidade": c.cidade or "", "plano": c.plano or "",
            "status": c.status or "", "sgp_id": c.sgp_id or "",
        }

    stamp = datetime.now(tz=UTC).strftime("%Y%m%d")
    if fmt == "xlsx":
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        assert ws is not None  # Workbook() sempre tem sheet ativa; satisfaz mypy
        ws.title = "clientes"
        ws.append(colunas)
        for c in clientes:
            r = _row(c)
            ws.append([r[k] for k in colunas])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="clientes-{stamp}.xlsx"'},
        )

    # CSV com BOM (Excel-friendly)
    sbuf = io.StringIO()
    sbuf.write("\ufeff")
    writer = csv.DictWriter(sbuf, fieldnames=colunas)
    writer.writeheader()
    for c in clientes:
        writer.writerow(_row(c))
    data = sbuf.getvalue().encode("utf-8")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="clientes-{stamp}.csv"'},
    )


@router.get("/segmento/valores", dependencies=[_admin_dep])
async def segmento_valores(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SegmentoValores:
    vals = await valores_distintos(session)
    return SegmentoValores(
        cidades=vals["cidades"], status=vals["status"], planos=vals["planos"]
    )


@router.post("/templates/sincronizar", dependencies=[_admin_dep])
async def sincronizar(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SyncResult:
    res = await sincronizar_templates(session, get_settings())
    return SyncResult(sincronizados=res["sincronizados"], canais=res["canais"])


@router.post("/templates", status_code=201, dependencies=[_admin_dep])
async def criar_template(
    body: TemplateUpsert,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BroadcastTemplateOut:
    existing = (
        await session.execute(
            select(BroadcastTemplate).where(BroadcastTemplate.name == body.name)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="template com esse nome já existe")
    t = BroadcastTemplate(
        name=body.name, language=body.language, category=body.category,
        variaveis=[v.model_dump() for v in body.variaveis],
        botoes=[b.model_dump() for b in body.botoes],
        header_tipo=body.header_tipo, ativo=body.ativo,
    )
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return BroadcastTemplateOut.model_validate(t, from_attributes=True)


@router.put("/templates/{template_id}", dependencies=[_admin_dep])
async def editar_template(
    template_id: UUID,
    body: TemplateUpsert,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BroadcastTemplateOut:
    t = (
        await session.execute(
            select(BroadcastTemplate).where(BroadcastTemplate.id == template_id)
        )
    ).scalar_one_or_none()
    if t is None:
        raise HTTPException(status_code=404, detail="template não encontrado")
    t.name = body.name
    t.language = body.language
    t.category = body.category
    t.variaveis = [v.model_dump() for v in body.variaveis]
    t.botoes = [b.model_dump() for b in body.botoes]
    t.header_tipo = body.header_tipo
    t.ativo = body.ativo
    await session.commit()
    await session.refresh(t)
    return BroadcastTemplateOut.model_validate(t, from_attributes=True)


@router.get("/{campanha_id}", dependencies=[_admin_dep])
async def get_campanha(
    campanha_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CampanhaDetail:
    repo = CampanhaRepo(session)
    c = await repo.get_by_id(campanha_id)
    if c is None:
        raise HTTPException(status_code=404, detail="campanha não encontrada")
    counts = await repo.status_counts(campanha_id)
    return CampanhaDetail(
        id=c.id, titulo=c.titulo, template_name=c.template_name, status=c.status,
        total_destinatarios=c.total_destinatarios, enviadas=c.enviadas, falhas=c.falhas,
        created_at=c.created_at, canal_id=c.canal_id, template_language=c.template_language,
        body_params=list(c.body_params or []), header_media_url=c.header_media_url,
        segmentacao=SegmentoFiltros.model_validate(c.segmentacao or {}),
        started_at=c.started_at, finished_at=c.finished_at, status_counts=counts,
    )


@router.post("/{campanha_id}/send", dependencies=[_admin_dep])
async def send_campanha(
    campanha_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    repo = CampanhaRepo(session)
    c = await repo.get_by_id(campanha_id)
    if c is None:
        raise HTTPException(status_code=404, detail="campanha não encontrada")
    if c.status not in {"rascunho", "erro"}:
        raise HTTPException(status_code=409, detail=f"campanha já está '{c.status}'")
    send_campanha_task.delay(str(campanha_id))
    return {"status": "enfileirada"}


@router.post("/{campanha_id}/cancel", dependencies=[_admin_dep])
async def cancel_campanha(
    campanha_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    repo = CampanhaRepo(session)
    c = await repo.get_by_id(campanha_id)
    if c is None:
        raise HTTPException(status_code=404, detail="campanha não encontrada")
    if c.status == "concluida":
        raise HTTPException(status_code=409, detail="campanha já concluída")
    c.status = "cancelada"
    await session.commit()
    return {"status": "cancelada"}


@router.post("/{campanha_id}/test", dependencies=[_admin_dep])
async def test_send(
    campanha_id: UUID,
    body: TestSendIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    repo = CampanhaRepo(session)
    c = await repo.get_by_id(campanha_id)
    if c is None:
        raise HTTPException(status_code=404, detail="campanha não encontrada")
    canal = (
        await session.execute(select(Canal).where(Canal.id == c.canal_id))
    ).scalar_one_or_none()
    if canal is None or canal.provider != "cloud":
        raise HTTPException(status_code=400, detail="canal inválido")
    adapter = build_for_canal(canal, get_settings())
    try:
        await adapter.send_template(
            body.whatsapp, name=c.template_name, language=c.template_language,
            body_params=list(c.body_params or []), header_media_url=c.header_media_url,
        )
    except WhatsAppError as e:
        raise HTTPException(status_code=502, detail=f"falha no envio: {e}") from e
    finally:
        await adapter.aclose()
    return {"status": "enviado"}


@router.post("/{campanha_id}/destinatarios/importar", dependencies=[_admin_dep])
async def importar_destinatarios(
    campanha_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
) -> ImportResult:
    repo = CampanhaRepo(session)
    camp = await repo.get_by_id(campanha_id)
    if camp is None:
        raise HTTPException(status_code=404, detail="campanha não encontrada")
    if camp.status not in {"rascunho", "erro"}:
        raise HTTPException(status_code=409, detail=f"campanha já está '{camp.status}'")

    tpl = (
        await session.execute(
            select(BroadcastTemplate).where(BroadcastTemplate.name == camp.template_name)
        )
    ).scalar_one_or_none()
    variaveis: list[dict[str, Any]] = tpl.variaveis if tpl is not None else []

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="arquivo vazio")
    rows, invalidos = parse_csv_destinatarios(content, variaveis)

    for r in rows:
        session.add(
            CampanhaDestinatario(
                campanha_id=camp.id,
                cliente_id=None,
                whatsapp=r["whatsapp"],
                body_params=r["body_params"],
                button_param=r["button_param"],
                status="pendente",
            )
        )
    camp.origem = "importado"
    camp.total_destinatarios = len(rows)
    await session.commit()
    return ImportResult(
        importados=len(rows), invalidos=len(invalidos), amostra_invalidos=invalidos[:10]
    )
