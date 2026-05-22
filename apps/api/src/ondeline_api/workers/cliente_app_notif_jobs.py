"""Jobs Celery de notificacoes do app cliente.

- `notify_faturas_vencendo` (daily): itera cliente_app_users ativos,
  consulta SGP, cria notif pra faturas vencendo em 3 dias / venceu ha 1 dia.
  Idempotente: nao duplica no mesmo dia/fatura.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select

from ondeline_api.adapters.sgp.linknetam import SgpLinkNetAMProvider
from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.cliente_app import (
    ClienteAppNotificacao,
    ClienteAppUser,
)
from ondeline_api.services.cliente_app_notif import notify_user
from ondeline_api.services.sgp_config import load_sgp_config
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import run_task, task_session

log = structlog.get_logger(__name__)


async def _ja_notificado_hoje(
    session: Any, user_id: Any, titulo_id: str, hoje: date
) -> bool:
    """Verifica se ja existe notif desse user com payload titulo_id no dia."""
    inicio = datetime.combine(hoje, datetime.min.time(), tzinfo=UTC)
    fim = inicio + timedelta(days=1)
    stmt = (
        select(ClienteAppNotificacao.id)
        .where(
            ClienteAppNotificacao.cliente_app_user_id == user_id,
            ClienteAppNotificacao.categoria == "fatura",
            ClienteAppNotificacao.created_at >= inicio,
            ClienteAppNotificacao.created_at < fim,
            ClienteAppNotificacao.payload_json["titulo_id"].astext == titulo_id,
        )
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def _run_faturas_vencendo() -> dict[str, int]:
    """Itera users ativos e dispara notifs por fatura vencendo."""
    criadas = 0
    erros = 0
    users_processados = 0
    hoje = datetime.now(tz=UTC).date()

    sgp_router: SgpRouter | None = None
    try:
        async with task_session() as session:
            sgp_ond = await load_sgp_config(session, "ondeline")
            sgp_lnk = await load_sgp_config(session, "linknetam")
            sgp_router = SgpRouter(
                primary=SgpOndelineProvider(**sgp_ond),
                secondary=SgpLinkNetAMProvider(**sgp_lnk),
            )

            stmt = select(ClienteAppUser).where(ClienteAppUser.status == "active")
            users = list((await session.execute(stmt)).scalars())

            for user in users:
                users_processados += 1
                try:
                    cpf = decrypt_pii(user.cpf_encrypted) if user.cpf_encrypted else ""
                    if not cpf:
                        continue
                    sgp_cliente = await sgp_router.buscar_por_cpf(cpf)
                    if sgp_cliente is None or not sgp_cliente.titulos:
                        continue

                    for fatura in sgp_cliente.titulos:
                        if fatura.status != "aberto":
                            continue
                        try:
                            venc = date.fromisoformat(fatura.vencimento)
                        except ValueError:
                            continue
                        dias = (venc - hoje).days

                        # Regras:
                        # - vence em 3 dias: aviso "fatura vencendo"
                        # - vence em 0 dias (hoje): aviso "vence hoje"
                        # - venceu ha 1 dia: aviso "fatura vencida"
                        if dias not in (3, 0, -1):
                            continue
                        if await _ja_notificado_hoje(
                            session, user.id, fatura.id, hoje
                        ):
                            continue

                        if dias == 3:
                            titulo = "Sua fatura vence em 3 dias"
                            corpo = (
                                f"R$ {fatura.valor:.2f} com vencimento em "
                                f"{venc.strftime('%d/%m/%Y')}."
                            )
                        elif dias == 0:
                            titulo = "Sua fatura vence hoje"
                            corpo = (
                                f"R$ {fatura.valor:.2f}. Pague pelo app antes "
                                "que entre em atraso."
                            )
                        else:  # -1
                            titulo = "Sua fatura venceu ontem"
                            corpo = (
                                f"R$ {fatura.valor:.2f} esta em atraso. "
                                "Regularize pra evitar suspensao."
                            )

                        notif = await notify_user(
                            session,
                            user.id,
                            "fatura",
                            titulo,
                            corpo,
                            action="tela:/home",
                            payload={
                                "titulo_id": fatura.id,
                                "valor": float(fatura.valor),
                                "vencimento": fatura.vencimento,
                                "dias": dias,
                            },
                        )
                        if notif is not None:
                            criadas += 1
                except Exception as e:
                    erros += 1
                    log.warning(
                        "notif_faturas.user_falhou",
                        user_id=str(user.id),
                        error=str(e),
                    )

            await session.commit()
    finally:
        if sgp_router is not None:
            await sgp_router.aclose()

    log.info(
        "notif_faturas.done",
        criadas=criadas,
        users_processados=users_processados,
        erros=erros,
    )
    return {
        "criadas": criadas,
        "users_processados": users_processados,
        "erros": erros,
    }


@celery_app.task(name="ondeline_api.workers.cliente_app_notif_jobs.notify_faturas_vencendo")
def notify_faturas_vencendo() -> dict[str, Any]:
    result: dict[str, Any] = run_task(_run_faturas_vencendo)
    return result
