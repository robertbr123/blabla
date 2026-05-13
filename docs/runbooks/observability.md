# Observability runbook — Ondeline v2

## Onde vê o quê

| Sinal | Endpoint / Lugar |
|---|---|
| Health | `GET /healthz` — DB + Redis + Celery queue depth |
| Liveness | `GET /livez` |
| Métricas | `GET /metrics` (Prometheus exposition format) |
| Logs | structlog JSON em stdout dos containers (api/worker/beat). PII (CPF/CNPJ/phone/email) mascarado automaticamente via `mask_pii` processor global. |
| Traces | OpenTelemetry → endpoint configurável em `OTEL_EXPORTER_OTLP_ENDPOINT` (default vazio = desligado). Instrumentado: FastAPI + Celery + HTTPX + SQLAlchemy + Redis. |
| Erros | Sentry → `SENTRY_DSN` (default vazio = desligado). PII scrubbed em `event.message` e breadcrumb messages via `_before_send`. |

## Env vars de observabilidade

| Var | Default | Significado |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Nível structlog. Aplica também ao stdlib root logger. |
| `ENV` | `development` | `development` usa ConsoleRenderer colorido; qualquer outro valor usa JSONRenderer. |
| `SENTRY_DSN` | (vazio) | Se setado, ativa Sentry no api/worker/beat. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | (vazio) | Ex: `http://tempo:4318` — ativa OTel. URL deve ser HTTP/protobuf, sem path. |
| `OTEL_SERVICE_NAME` | `ondeline-api` | Prefixo do `service.name` (sufixos: `-api`, `-worker`, `-beat`). |

## LGPD

| Operação | Endpoint / Job |
|---|---|
| Exportar dados de um cliente | `GET /api/v1/clientes/{id}/export` (admin) → ZIP com `cliente.json` + `conversas.json` + `ordens_servico.json` + `README.txt` |
| Marcar cliente para purge | `DELETE /api/v1/clientes/{id}` (admin) → seta `deleted_at` e `retention_until = now + 30d` |
| Purge automático | `lgpd_purge_job` (Celery beat, daily 03:00) → hard-delete onde `retention_until < now` |
| Particionamento de `mensagens` | `ensure_future_mensagens_partitions` (Celery beat, daily 02:30) → cria próximas 3 partições idempotentemente |

## Healthcheck Docker

- `api` → `curl /livez` (a cada 10s, definido no Dockerfile)
- `worker` → `celery inspect ping -d celery@$HOSTNAME` (a cada 30s, definido em docker-compose.dev.yml)
- `beat` → schedule file `/tmp/celerybeat-schedule` existe e mtime < 2 min (a cada 30s)
- `postgres`, `redis` → próprios (pg_isready, redis-cli ping)

## Quando algo está errado

| Sintoma | O que checar |
|---|---|
| 503 em `/healthz` | Campo `checks.db` ou `checks.redis` mostra error. Inspecionar logs do container do componente que falhou. |
| Worker `unhealthy` | `docker logs ondeline-worker` + dentro do container: `celery -A ondeline_api.workers.celery_app:celery_app inspect active`. |
| Filas crescendo (`celery` field em `/healthz` com counts altos) | Worker scaled-down, tarefa travada, ou pico de tráfego. Inspecionar logs do worker. |
| Sem traces no backend OTel | `OTEL_EXPORTER_OTLP_ENDPOINT` setado? Endpoint acessível do container (try `curl` de dentro)? `BatchSpanProcessor` faz batching — esperar ~30s antes de concluir que nada está saindo. |
| Sem erros no Sentry | `SENTRY_DSN` setado? Sentry quota não esgotou? `_before_send` retornou `None`? |
| Particionamento atrasado | `mensagens_YYYY_MM` não existe para o mês corrente — checar logs do beat e do worker `default` queue. Pode rodar manualmente: `celery -A ondeline_api.workers.celery_app:celery_app call ondeline_api.workers.partition_jobs.ensure_future_mensagens_partitions`. |

## Dashboards Grafana

JSON importáveis em `infra/grafana/dashboards/` — ver `infra/grafana/README.md` para instruções de import e config do data source Prometheus.

- `ondeline-operational.json` — 8 painéis: webhook rates, dedup ratio, evolution success rate, process CPU/memory
- `ondeline-product.json` — placeholder para KPIs de produto (requer Postgres data source plugin, deferido pós-cutover)
