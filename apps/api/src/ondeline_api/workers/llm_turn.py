"""Task Celery: roda 1 turno do LLM para uma Conversa."""
from __future__ import annotations

from typing import Any, cast
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select

import ondeline_api.tools.abrir_ordem_servico
import ondeline_api.tools.buscar_cliente_sgp
import ondeline_api.tools.consultar_manutencoes
import ondeline_api.tools.consultar_planos
import ondeline_api.tools.consultar_rede
import ondeline_api.tools.enviar_boleto

# Importacoes que registram as tools no registry global
import ondeline_api.tools.transferir_para_humano  # noqa: F401
from ondeline_api.adapters.llm.hermes import HermesProvider
from ondeline_api.adapters.sgp.linknetam import SgpLinkNetAMProvider
from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.adapters.whatsapp import WhatsAppAdapter
from ondeline_api.config import get_settings
from ondeline_api.db.models.business import (
    Cliente,
    Conversa,
    ConversaStatus,
    MensagemRole,
)
from ondeline_api.repositories.mensagem import MensagemRepo
from ondeline_api.services.canal_whatsapp import adapter_for_conversa
from ondeline_api.services.llm_loop import run_turn
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.services.sgp_config import load_sgp_config
from ondeline_api.services.tokens_budget import TokensBudget
from ondeline_api.tools.context import ToolContext
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import get_redis, run_task, task_session

log = structlog.get_logger(__name__)

# Runway de requeue (MAX_REQUEUES x REQUEUE_DELAY_SECONDS = 300s) tem que ser
# MAIOR que o lock TTL derivado em _run (~210s no pior caso), pra um turno
# legitimo terminar e liberar o lock antes do requeue desistir.
MAX_REQUEUES = 30
REQUEUE_DELAY_SECONDS = 10

# Compare-and-delete atomico: so deleta o lock se o valor ainda for o nosso
# token. Evita que o turno A (cujo TTL expirou) delete o lock do turno B.
_RELEASE_LOCK_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


def _skip_reason(status: ConversaStatus, last_role: MensagemRole | None) -> str | None:
    """None = turno deve rodar; senao, motivo do skip.

    - Conversa fora de BOT: atendente assumiu / escalou / encerrou entre o
      enfileiramento e a execucao - bot NAO pode responder por cima.
    - Ultima mensagem nao e do cliente: um turno anterior (concorrente,
      serializado pelo lock) ja respondeu - evita resposta duplicada.
    """
    if status is not ConversaStatus.BOT:
        return f"status_{status.value}"
    if last_role is not None and last_role is not MensagemRole.CLIENTE:
        return "ja_respondida"
    return None


async def _run(conversa_id: UUID) -> dict[str, Any]:
    s = get_settings()
    redis = await get_redis()

    # TTL precisa cobrir o pior caso de turno (max_iter chamadas de LLM no
    # timeout maximo) + folga pra I/O (DB/SGP/WhatsApp). Derivado da config
    # pra nao drifar se os settings mudarem.
    lock_ttl = int(s.llm_max_iter * s.llm_timeout_seconds) + 60

    # Lock por conversa: serializa turnos concorrentes (3 msgs seguidas do
    # cliente = 3 tasks). Quem nao pega o lock e re-enfileirado pela task.
    lock_key = f"llm:lock:{conversa_id}"
    lock_token = uuid4().hex
    got_lock = bool(await redis.set(lock_key, lock_token, nx=True, ex=lock_ttl))
    if not got_lock:
        log.info("llm_turn.locked", conversa_id=str(conversa_id))
        return {"conversa_id": str(conversa_id), "skipped": "locked"}

    try:
        llm_url, llm_key, llm_model = s.effective_llm()
        provider = HermesProvider(
            base_url=llm_url,
            model=llm_model,
            api_key=llm_key,
            timeout=s.llm_timeout_seconds,
        )
        budget = TokensBudget(redis, daily_limit=s.llm_max_tokens_per_conversa_dia)
        router: SgpRouter | None = None
        evolution: WhatsAppAdapter | None = None

        try:
            async with task_session() as session:
                # F4 + Cloud: devolve EvolutionAdapter OU CloudAdapter conforme
                # canal.provider da conversa. Variavel mantem nome 'evolution'
                # por compat com ToolContext / 5+ call sites em llm_loop e tools.
                evolution = await adapter_for_conversa(session, conversa_id, s)
                sgp_ond = await load_sgp_config(session, "ondeline")
                sgp_lnk = await load_sgp_config(session, "linknetam")
                router = SgpRouter(
                    primary=SgpOndelineProvider(**sgp_ond),
                    secondary=SgpLinkNetAMProvider(**sgp_lnk),
                )
                conversa = (
                    await session.execute(select(Conversa).where(Conversa.id == conversa_id))
                ).scalar_one()
                # Guards: status pode ter mudado e/ou outro turno ja respondeu.
                history = await MensagemRepo(session).list_history(conversa_id, limit=1)
                last_role = history[-1].role if history else None
                reason = _skip_reason(conversa.status, last_role)
                if reason is not None:
                    log.info("llm_turn.skip", conversa_id=str(conversa_id), reason=reason)
                    return {"conversa_id": str(conversa_id), "skipped": reason}
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
                    redis=redis,
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
            if evolution is not None:
                await evolution.aclose()
    finally:
        # Libera o lock SEMPRE (apos commit da task_session), mas so se ainda
        # for o nosso token. O TTL derivado e o backstop se o worker morrer.
        try:
            released = await redis.eval(  # type: ignore[no-untyped-call]
                _RELEASE_LOCK_LUA, 1, lock_key, lock_token
            )
            if not released:
                # lock expirou durante o turno e (possivelmente) outro turno
                # ja esta rodando - nao deletamos o lock dele
                log.warning("llm_turn.lock_expired_during_turn", conversa_id=str(conversa_id))
        except Exception:
            log.warning("llm_turn.lock_release_failed", conversa_id=str(conversa_id))


@celery_app.task(
    name="ondeline_api.workers.llm_turn.llm_turn_task",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def llm_turn_task(self: Any, *, conversa_id: str, requeued: int = 0) -> dict[str, Any]:
    cid = UUID(conversa_id)
    try:
        result = cast(dict[str, Any], run_task(lambda: _run(cid)))
    except Exception as e:
        raise self.retry(exc=e) from e
    if result.get("skipped") == "locked":
        if requeued < MAX_REQUEUES:
            # Outro turno esta rodando: tenta de novo em alguns segundos. O guard
            # "ja_respondida" garante que o requeue nao gera resposta duplicada.
            llm_turn_task.apply_async(
                kwargs={"conversa_id": conversa_id, "requeued": requeued + 1},
                countdown=REQUEUE_DELAY_SECONDS,
            )
        else:
            log.warning("llm_turn.requeue_exhausted", conversa_id=conversa_id, requeued=requeued)
    return result
