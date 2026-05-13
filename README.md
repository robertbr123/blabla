# Ondeline v2

[![CI](https://github.com/robertbr123/blabla/actions/workflows/ci.yml/badge.svg)](https://github.com/robertbr123/blabla/actions/workflows/ci.yml)

Reescrita paralela do bot de WhatsApp + dashboard da Ondeline Telecom.

**Status:** M1–M9 prontos (cutover-ready). Ver `docs/runbooks/cutover.md` para o passo a passo do big-bang.

## Stack

- Backend: FastAPI + Celery (Python 3.11)
- Banco: PostgreSQL 16 (Docker)
- Cache/fila: Redis 7
- Frontend: Next.js 15 (dashboard admin/atendente + PWA do técnico)
- Observabilidade: structlog (PII-masked) + Prometheus `/metrics` + OpenTelemetry + Sentry (todos opt-in via env)

## Comandos rápidos

| Comando | O quê |
|---|---|
| `make dev` | Sobe stack de dev (postgres + redis + api) |
| `make down` | Derruba stack |
| `make test` | Roda pytest |
| `make lint` | Roda ruff + mypy |
| `make logs` | Tail dos logs dos containers |

## Documentação

- Spec de design: [docs/superpowers/specs/2026-05-09-ondeline-v2-fase1-fase2-design.md](docs/superpowers/specs/2026-05-09-ondeline-v2-fase1-fase2-design.md)
- Planos por milestone: [docs/superpowers/plans/](docs/superpowers/plans/)
- Runbook de observabilidade: [docs/runbooks/observability.md](docs/runbooks/observability.md)
- Runbook de cutover: [docs/runbooks/cutover.md](docs/runbooks/cutover.md)

## Setup local

```bash
cp .env.example .env
# editar .env com seus secrets
make dev
curl http://localhost:8000/healthz
```

## Cutover (M9)

Tudo que você precisa pra fazer o big-bang está em:

- **Runbook**: `docs/runbooks/cutover.md` — T-7d → T+7d com comandos e rollback
- **Scripts**:
  - `scripts/archive-v1.sh` — snapshot do v1 em `/root/BLABLA/ondeline-archive/`
  - `scripts/smoke-prod.sh` — smoke health/metrics/webhook (use `API_BASE=...` para apontar)
  - `scripts/check-hermes.sh` — confirma Hermes-3 gateway via `/v1/models`
  - `scripts/seed-admin.sh` — cria o primeiro admin idempotentemente
  - `infra/pg_dump_local.sh` — backup diário do Postgres (cron-friendly)
- **Compose de prod**: `infra/docker-compose.prod.yml`
- **Dashboards Grafana**: `infra/grafana/dashboards/*.json` — ver `infra/grafana/README.md`

Pré-requisitos antes de seguir o runbook: `.env` populado com `JWT_SECRET`,
`PII_ENCRYPTION_KEY`, `PII_HASH_PEPPER`, `EVOLUTION_HMAC_SECRET`, `EVOLUTION_KEY`,
`ADMIN_EMAIL`, `ADMIN_PASSWORD`. Veja `.env.example` para a lista completa.
