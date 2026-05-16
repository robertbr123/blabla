"""Regressao guard: todas as tasks que o codigo chama via .delay devem estar
registradas no Celery app. Sem isso, o worker recebe a task e descarta com
'unregistered task of type ...' (foi o que aconteceu com followup_os_task em
prod).
"""
from __future__ import annotations

import importlib

from ondeline_api.workers.celery_app import celery_app

# Forca importacao dos modulos listados em include=. No worker em prod, o
# Celery faz isso ao iniciar; no teste, precisamos simular.
for _mod in celery_app.conf.include or []:
    importlib.import_module(_mod)

# Tasks que outro codigo enfileira via .delay. Cada uma DEVE estar registrada
# no Celery app, e a forma de garantir e listar o modulo no `include=` do
# create_celery_app. Esse teste falha rapido se alguem mover ou esquecer.
EXPECTED_TASKS = {
    "ondeline_api.workers.inbound.process_inbound_message_task",
    "ondeline_api.workers.outbound.send_outbound_task",
    "ondeline_api.workers.llm_turn.llm_turn_task",
    "ondeline_api.workers.followup.followup_os_task",
    "ondeline_api.workers.notify_sender.flush_pending",
    "ondeline_api.workers.notify_jobs.run_planner_jobs",
    "ondeline_api.workers.notify_jobs.followup_os_job",
    "ondeline_api.workers.notify_jobs.manutencao_job",
    "ondeline_api.workers.notify_jobs.lgpd_purge_job",
    "ondeline_api.workers.partition_jobs.ensure_future_mensagens_partitions",
}


def test_todas_tasks_estao_registradas() -> None:
    registered = set(celery_app.tasks.keys())
    missing = EXPECTED_TASKS - registered
    assert not missing, (
        f"Tasks ausentes do celery_app (faltam no `include=`): {sorted(missing)}"
    )
