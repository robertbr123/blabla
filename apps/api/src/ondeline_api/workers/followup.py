"""Task Celery: atualiza OS e envia mensagem de resultado do follow-up."""
from __future__ import annotations

import re
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select

from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import run_task, task_session

log = structlog.get_logger(__name__)

# Captura primeiro digito 1-5 isolado ou apos "nota". Ignora numeros >5 (datas, OS, etc).
_CSAT_RE = re.compile(r"(?:^|\s|nota\s*)([1-5])(?:\s|$|\.|,|!|\?|🌟)")


def _parse_csat(text: str | None) -> int | None:
    if not text:
        return None
    m = _CSAT_RE.search(text.lower().strip())
    return int(m.group(1)) if m else None

_MSG_CONFIRMAR = (
    "Que bom que ficou tudo certo! 🎉\n\n"
    "Sua avaliação ajuda muito a melhorar — se ainda não mandou, "
    "responde com uma nota de *1 a 5* (5 = excelente atendimento). 🌟"
)
_MSG_ESCALAR = (
    "Entendido, vou acionar nossa equipe agora pra resolver o que ficou pendente. "
    "Em breve um atendente entrará em contato. 🙏"
)


async def _run_followup(conversa_id: UUID, resultado: str, resposta: str) -> None:
    from ondeline_api.adapters.evolution import EvolutionAdapter
    from ondeline_api.config import get_settings
    from ondeline_api.db.models.business import Conversa, OrdemServico
    from ondeline_api.services import business_hours

    s = get_settings()
    evo = EvolutionAdapter(base_url=s.evolution_url, instance=s.evolution_instance, api_key=s.evolution_key)
    try:
        async with task_session() as session:
            conversa = (
                await session.execute(select(Conversa).where(Conversa.id == conversa_id))
            ).scalar_one_or_none()
            if conversa is None:
                log.warning("followup.conversa_not_found", conversa_id=str(conversa_id))
                return

            msg = (
                _MSG_CONFIRMAR
                if resultado == "ok"
                else business_hours.humano_message(
                    _MSG_ESCALAR,
                    closed_prefix=(
                        "Entendido, vou acionar nossa equipe pra resolver o que ficou pendente."
                    ),
                )
            )
            try:
                await evo.send_text(conversa.whatsapp, msg)
            except Exception:
                log.warning("followup.send_failed", whatsapp=conversa.whatsapp, exc_info=True)

            if conversa.followup_os_id:
                from datetime import UTC, datetime
                os_ = (
                    await session.execute(
                        select(OrdemServico).where(OrdemServico.id == conversa.followup_os_id)
                    )
                ).scalar_one_or_none()
                if os_:
                    os_.follow_up_resultado = resultado
                    os_.follow_up_resposta = resposta
                    os_.follow_up_respondido_em = datetime.now(tz=UTC)
                    csat = _parse_csat(resposta)
                    if csat is not None and os_.csat is None:
                        os_.csat = csat
                        log.info(
                            "followup.csat_extracted",
                            os_id=str(os_.id),
                            csat=csat,
                        )
            conversa.followup_os_id = None
    finally:
        await evo.aclose()


@celery_app.task(
    name="ondeline_api.workers.followup.followup_os_task",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
)
def followup_os_task(self: Any, *, conversa_id: str, resultado: str, resposta: str) -> None:
    cid = UUID(conversa_id)
    try:
        run_task(lambda: _run_followup(cid, resultado, resposta))
    except Exception as e:
        raise self.retry(exc=e) from e
