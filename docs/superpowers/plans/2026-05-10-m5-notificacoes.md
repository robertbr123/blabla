# M5 — Notificações: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Adicionar Celery Beat + jobs agendados pra notificações proativas: vencimento, atraso, pagamento detectado, follow-up OS (CSAT), e broadcast de manutenções planejadas. Worker que processa a fila `Notificacao` enviando via Evolution.

**Architecture:** Beat scheduler dispara jobs a cada N minutos. Cada job consulta DB+SGP, cria registros `Notificacao` (tipo+agendada_para+payload). Worker processa a fila, envia via `EvolutionAdapter`, marca `enviada_em`. Reuso de tudo do M4 (SGP cache, tools opcionalmente).

**Tech Stack:** Celery beat (já em deps M3), `Notificacao` model (já em M2), `EvolutionAdapter`+`SgpCacheService` (M3+M4).

**Pré-requisitos:** Tag `m4-sgp-hermes-tools` aplicada, CI verde.

---

## File Structure

```
apps/api/src/ondeline_api/
├── workers/
│   ├── beat_schedule.py        # NEW — beat schedule config
│   ├── notify_jobs.py           # NEW — 5 jobs scheduled
│   └── notify_sender.py         # NEW — processa fila Notificacao
├── services/
│   ├── notify_planner.py        # NEW — logica que decide quem notificar
│   └── notify_sender.py         # NEW — envia 1 Notificacao
├── repositories/
│   └── notificacao.py           # NEW — CRUD Notificacao
infra/
├── docker-compose.dev.yml       # MODIFY — add beat service
.github/workflows/ci.yml         # NO-OP (jobs run lazily, beat not started in CI)
```

---

## Task 1: NotificacaoRepo + Beat schedule scaffolding

Create `apps/api/src/ondeline_api/repositories/notificacao.py`:

```python
"""NotificacaoRepo — CRUD + dedup por (cliente_id, tipo, agendada_para)."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import (
    Notificacao,
    NotificacaoStatus,
    NotificacaoTipo,
)


class NotificacaoRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def already_scheduled(
        self,
        *,
        cliente_id: UUID,
        tipo: NotificacaoTipo,
        agendada_para: datetime,
    ) -> bool:
        stmt = select(Notificacao.id).where(
            and_(
                Notificacao.cliente_id == cliente_id,
                Notificacao.tipo == tipo,
                Notificacao.agendada_para == agendada_para,
            )
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def schedule(
        self,
        *,
        cliente_id: UUID,
        tipo: NotificacaoTipo,
        agendada_para: datetime,
        payload: dict[str, Any],
    ) -> Notificacao | None:
        if await self.already_scheduled(
            cliente_id=cliente_id, tipo=tipo, agendada_para=agendada_para
        ):
            return None
        n = Notificacao(
            cliente_id=cliente_id,
            tipo=tipo,
            agendada_para=agendada_para,
            payload=payload,
            status=NotificacaoStatus.PENDENTE,
        )
        self._session.add(n)
        await self._session.flush()
        return n

    async def list_due(self, *, now: datetime, limit: int = 100) -> list[Notificacao]:
        stmt = (
            select(Notificacao)
            .where(
                Notificacao.status == NotificacaoStatus.PENDENTE,
                Notificacao.agendada_para <= now,
            )
            .order_by(Notificacao.agendada_para)
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def mark_sent(self, n: Notificacao) -> None:
        n.status = NotificacaoStatus.ENVIADA
        n.enviada_em = datetime.now(tz=__import__("datetime").UTC)
        await self._session.flush()

    async def mark_failed(self, n: Notificacao) -> None:
        n.tentativas += 1
        if n.tentativas >= 3:
            n.status = NotificacaoStatus.FALHA
        await self._session.flush()
```

Tests: `apps/api/tests/test_repo_notificacao.py` covering schedule (creates), schedule (dedup returns None), list_due (filters by status+date), mark_sent, mark_failed (3rd attempt → FALHA).

Commit: `feat(m5): add NotificacaoRepo with dedup and lifecycle`

---

## Task 2: Beat schedule config

Create `apps/api/src/ondeline_api/workers/beat_schedule.py`:

```python
"""Celery Beat schedule config.

Jobs:
- planner_jobs (every 30min):  vencimentos + atrasos + pagamentos
- followup_os_job (every 1h):  envia CSAT 24h apos OS concluida
- manutencao_job (every 15min): broadcast manutencoes proximas
- send_notifications (every 1min): processa fila Notificacao pendente
- lgpd_purge_job (daily 03:00): deleta registros expirados (retention_until < now)
"""
from __future__ import annotations

from celery.schedules import crontab


BEAT_SCHEDULE: dict[str, dict] = {
    "vencimentos-atrasos-pagamentos": {
        "task": "ondeline_api.workers.notify_jobs.run_planner_jobs",
        "schedule": crontab(minute="*/30"),
    },
    "follow-up-os": {
        "task": "ondeline_api.workers.notify_jobs.followup_os_job",
        "schedule": crontab(minute=0),  # hourly
    },
    "manutencoes": {
        "task": "ondeline_api.workers.notify_jobs.manutencao_job",
        "schedule": crontab(minute="*/15"),
    },
    "send-pending-notifications": {
        "task": "ondeline_api.workers.notify_sender.flush_pending",
        "schedule": crontab(minute="*"),  # every minute
    },
    "lgpd-purge": {
        "task": "ondeline_api.workers.notify_jobs.lgpd_purge_job",
        "schedule": crontab(hour=3, minute=0),
    },
}
```

Update `workers/celery_app.py` to load: `app.conf.beat_schedule = BEAT_SCHEDULE` and add the jobs to `include`.

Commit: `feat(m5): add beat schedule config`

---

## Task 3: notify_planner service + notify_jobs.run_planner_jobs

Create `apps/api/src/ondeline_api/services/notify_planner.py` with functions:

- `async def schedule_vencimentos(session, sgp_cache, today_offset_days=3) -> int`:
  para cada Cliente ativo, consulta SGP (via cache), encontra titulos com vencimento entre [hoje, hoje+offset], chama `repo.schedule(tipo=VENCIMENTO, agendada_para=hoje 09:00, payload={fatura_ids, valor_total, vencimento})`. Returns count agendado.
- `async def schedule_atrasos(session, sgp_cache) -> int`:
  similar mas para titulos vencidos há 1, 7, 15 dias. payload tem dias_atraso.
- `async def schedule_pagamentos(session, sgp_cache) -> int`:
  varre últimas N notificações de VENCIMENTO/ATRASO recentes. Re-consulta SGP. Se titulo virou "pago", agenda PAGAMENTO (parabéns).

Create `apps/api/src/ondeline_api/workers/notify_jobs.py` com a task celery `run_planner_jobs` que invoca os 3 services + log do count.

Tests com fakes (FakeSgpProvider scriptado, db_session real). Min 6 testes.

Commit: `feat(m5): add notify_planner service + run_planner_jobs task`

---

## Task 4: follow_up_os_job + manutencao_job + lgpd_purge_job

Add to `services/notify_planner.py`:

- `async def schedule_followup_os(session) -> int`: queries OrdemServico WHERE status=concluida AND concluida_em < now-24h AND not yet notified → agenda OS_CONCLUIDA com payload pedindo CSAT.
- `async def broadcast_manutencao(session) -> int`: for each Manutencao com inicio_at em [now, now+1h], for each Cliente em cliente.cidade in manutencao.cidades, agenda notificação tipo VENCIMENTO (ou criar novo tipo MANUTENCAO — mas para evitar migration, usa VENCIMENTO com payload.kind="manutencao"). Actually simpler: add `MANUTENCAO` to NotificacaoTipo via migration 0004.

Wait — adding to enum requires migration. Simpler path: piggyback on existing tipos. OS_CONCLUIDA é claro. Para manutenção, posso usar payload.kind discriminador dentro de PAGAMENTO ou VENCIMENTO — mas é confuso. **Decisão pragmática**: criar migration 0004 que adiciona MANUTENCAO ao enum.

Create migration `0004_add_manutencao_notif_tipo.py`:

```python
def upgrade() -> None:
    op.execute("ALTER TYPE notificacao_tipo ADD VALUE IF NOT EXISTS 'manutencao'")

def downgrade() -> None:
    pass  # Postgres nao suporta DROP VALUE em enum nativo
```

Actually our enum is `native_enum=False` — armazenado como VARCHAR via SQLAlchemy enum constraint. Mais simples: só adicionar `MANUTENCAO = "manutencao"` ao Python enum. Postgres aceita qualquer string.

Add `MANUTENCAO = "manutencao"` to `NotificacaoTipo` in `db/models/business.py`. Sem migration necessária.

Add `lgpd_purge_job` task:
- delete clientes WHERE retention_until < now
- delete conversas WHERE retention_until < now
- log count purgado

Tests covering each path.

Commit: `feat(m5): add followup_os, manutencao broadcast, and LGPD purge jobs`

---

## Task 5: notify_sender — processa fila Notificacao

Create `apps/api/src/ondeline_api/services/notify_sender.py`:

- `async def render_message(n: Notificacao, cliente_nome: str) -> str`: formata mensagem por tipo (vencimento "Olá Joao! Sua fatura vence em 3 dias..." etc.)
- `async def send_one(session, evolution, n: Notificacao) -> bool`: decrypt cliente.nome, render, evolution.send_text. Return True/False.

Create `apps/api/src/ondeline_api/workers/notify_sender.py`:

- task `flush_pending`: lista 100 notificações due, chama send_one, mark_sent ou mark_failed.

Tests: render_message para cada tipo (5 tipos), send_one (sucesso e falha), flush_pending integração.

Commit: `feat(m5): add notify_sender — render and send pending notifications`

---

## Task 6: docker-compose beat service + smoke + CI + tag

Add `beat` service ao `infra/docker-compose.dev.yml`:

```yaml
  beat:
    build:
      context: ../apps/api
      dockerfile: Dockerfile
    container_name: ondeline-beat
    command: ["celery", "-A", "ondeline_api.workers.celery_app:celery_app", "beat", "--loglevel=info"]
    environment: ...
    env_file: [../.env]
    depends_on: [postgres, redis]
    restart: unless-stopped
```

Smoke: `make dev`, verify `beat` container ready, sleep 60s, query DB and check that planner jobs ran (look for INFO log "planner_jobs.completed").

Push, watch CI.

Tag `m5-notificacoes`.

Commit: `feat(m5): add celery beat container + tag`

---

## DoD

- [ ] NotificacaoRepo with dedup + lifecycle (PENDENTE → ENVIADA/FALHA)
- [ ] Beat schedule has 5 jobs
- [ ] 5 planner jobs working (vencimentos, atrasos, pagamentos, follow-up OS, manutenções)
- [ ] LGPD purge job deletes expired records
- [ ] notify_sender renders + envia + marca status
- [ ] Beat container sobe via make dev
- [ ] Full suite green, CI green
- [ ] Tag m5-notificacoes
