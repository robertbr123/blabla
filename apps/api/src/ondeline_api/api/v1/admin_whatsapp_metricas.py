"""Router admin pra metricas de templates WhatsApp Cloud.

Le ``whatsapp_message_status`` (populada na Fase 2.2a) e agrega por
``template_name`` numa janela temporal. Mostra taxa de entrega
(delivered/sent), taxa de leitura (read/sent) e falhas.

Fase 2.2b do plano de evolucao.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.business import WhatsAppMessageStatus
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db

router = APIRouter(
    prefix="/api/v1/admin/whatsapp-metricas",
    tags=["admin:whatsapp-metricas"],
)


class TemplateStats(BaseModel):
    template_name: str
    sent: int
    delivered: int
    read: int
    failed: int
    # Taxas em fracao 0.0-1.0
    delivery_rate: float
    read_rate: float
    failure_rate: float


class WhatsAppMetricasOut(BaseModel):
    since: datetime
    days: int
    items: list[TemplateStats]
    # Totais consolidados (todos templates)
    total_sent: int
    total_delivered: int
    total_read: int
    total_failed: int


@router.get("", response_model=WhatsAppMetricasOut)
async def get_whatsapp_metricas(
    days: int = Query(default=7, ge=1, le=90),
    _user: User = Depends(require_role(Role.ADMIN)),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> WhatsAppMetricasOut:
    """Agrega metricas dos ultimos N dias por template_name.

    COUNT(col) ignora NULL — entao COUNT(delivered_at) conta apenas as que
    receberam status delivered. Mesma logica pra read e failed.
    """
    since = datetime.now(UTC) - timedelta(days=days)

    stmt = (
        select(
            WhatsAppMessageStatus.template_name,
            func.count().label("sent"),
            func.count(WhatsAppMessageStatus.delivered_at).label("delivered"),
            func.count(WhatsAppMessageStatus.read_at).label("read"),
            func.count(WhatsAppMessageStatus.failed_at).label("failed"),
        )
        .where(
            WhatsAppMessageStatus.sent_at >= since,
            WhatsAppMessageStatus.template_name.is_not(None),
        )
        .group_by(WhatsAppMessageStatus.template_name)
        .order_by(func.count().desc())
    )
    rows = (await session.execute(stmt)).all()

    items: list[TemplateStats] = []
    total_sent = total_delivered = total_read = total_failed = 0
    for r in rows:
        sent = int(r.sent or 0)
        delivered = int(r.delivered or 0)
        read = int(r.read or 0)
        failed = int(r.failed or 0)
        items.append(
            TemplateStats(
                template_name=str(r.template_name or "—"),
                sent=sent,
                delivered=delivered,
                read=read,
                failed=failed,
                delivery_rate=delivered / sent if sent > 0 else 0.0,
                read_rate=read / sent if sent > 0 else 0.0,
                failure_rate=failed / sent if sent > 0 else 0.0,
            )
        )
        total_sent += sent
        total_delivered += delivered
        total_read += read
        total_failed += failed

    return WhatsAppMetricasOut(
        since=since,
        days=days,
        items=items,
        total_sent=total_sent,
        total_delivered=total_delivered,
        total_read=total_read,
        total_failed=total_failed,
    )
