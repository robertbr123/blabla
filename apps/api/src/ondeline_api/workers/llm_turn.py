"""Task Celery: roda 1 turno do LLM para uma Conversa."""
from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import structlog
from sqlalchemy import select

import ondeline_api.tools.abrir_ordem_servico
import ondeline_api.tools.buscar_cliente_sgp
import ondeline_api.tools.consultar_manutencoes
import ondeline_api.tools.consultar_planos
import ondeline_api.tools.enviar_boleto

# Importacoes que registram as 6 tools no registry global
import ondeline_api.tools.transferir_para_humano  # noqa: F401
from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.adapters.llm.hermes import HermesProvider
from ondeline_api.adapters.sgp.linknetam import SgpLinkNetAMProvider
from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.config import get_settings
from ondeline_api.db.models.business import Cliente, Conversa
from ondeline_api.services.llm_loop import run_turn
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.services.sgp_config import load_sgp_config
from ondeline_api.services.tokens_budget import TokensBudget
from ondeline_api.tools.context import ToolContext
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import get_redis, run_task, task_session

log = structlog.get_logger(__name__)


async def _run(conversa_id: UUID) -> dict[str, Any]:
    s = get_settings()
    redis = await get_redis()
    evolution = EvolutionAdapter(
        base_url=s.evolution_url, instance=s.evolution_instance, api_key=s.evolution_key
    )
    llm_url, llm_key, llm_model = s.effective_llm()
    provider = HermesProvider(
        base_url=llm_url,
        model=llm_model,
        api_key=llm_key,
        timeout=s.llm_timeout_seconds,
    )
    budget = TokensBudget(redis, daily_limit=s.llm_max_tokens_per_conversa_dia)
    router: SgpRouter | None = None

    try:
        async with task_session() as session:
            sgp_ond = await load_sgp_config(session, "ondeline")
            sgp_lnk = await load_sgp_config(session, "linknetam")
            router = SgpRouter(
                primary=SgpOndelineProvider(**sgp_ond),
                secondary=SgpLinkNetAMProvider(**sgp_lnk),
            )
            conversa = (
                await session.execute(select(Conversa).where(Conversa.id == conversa_id))
            ).scalar_one()
            cliente = None
            if conversa.cliente_id:
                cliente = (
                    await session.execute(
                        select(Cliente).where(Cliente.id == conversa.cliente_id)
                    )
                ).scalar_one_or_none()
            cache = SgpCacheService(
                redis=redis,
                session=session,
                router=router,
                ttl_cliente=s.sgp_cache_ttl_cliente,
                ttl_negativo=s.sgp_cache_ttl_negativo,
            )
            ctx = ToolContext(
                session=session,
                conversa=conversa,
                cliente=cliente,
                evolution=evolution,
                sgp_router=router,
                sgp_cache=cache,
            )
            outcome = await run_turn(
                ctx=ctx,
                provider=provider,
                model=llm_model,
                history_turns=s.llm_history_turns,
                max_iter=s.llm_max_iter,
                budget=budget,
            )
        log.info(
            "llm_turn.done",
            conversa_id=str(conversa_id),
            tokens=outcome.tokens_used,
            iterations=outcome.iterations,
            tools=outcome.tool_calls_made,
            escalated=outcome.escalated,
        )
        return {
            "conversa_id": str(conversa_id),
            "tokens": outcome.tokens_used,
            "iterations": outcome.iterations,
            "escalated": str(outcome.escalated).lower(),
        }
    finally:
        await provider.aclose()
        if router is not None:
            await router.aclose()
        await evolution.aclose()


@celery_app.task(
    name="ondeline_api.workers.llm_turn.llm_turn_task",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def llm_turn_task(self: Any, *, conversa_id: str) -> dict[str, Any]:
    cid = UUID(conversa_id)
    try:
        return cast(dict[str, Any], run_task(lambda: _run(cid)))
    except Exception as e:
        raise self.retry(exc=e) from e
