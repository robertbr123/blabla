# BLABLAv2

[![CI](https://github.com/robertbr123/blabla/actions/workflows/ci.yml/badge.svg)](https://github.com/robertbr123/blabla/actions/workflows/ci.yml)
[![Deploy](https://github.com/robertbr123/blabla/actions/workflows/deploy.yml/badge.svg)](https://github.com/robertbr123/blabla/actions/workflows/deploy.yml)

Bot WhatsApp + dashboard admin + PWA do técnico para a Ondeline Telecom.  
Monorepo com 3 apps: API (FastAPI), Dashboard (Next.js) e PWA técnico (Next.js).

---

## Índice

- [Arquitetura](#arquitetura)
- [Stack](#stack)
- [Deploy em produção (VPS + GHCR)](#deploy-em-produção-vps--ghcr)
- [Desenvolvimento local](#desenvolvimento-local)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Serviços Docker](#serviços-docker)
- [Comandos úteis](#comandos-úteis)
- [Banco de dados e migrações](#banco-de-dados-e-migrações)
- [Observabilidade](#observabilidade)
- [Scripts operacionais](#scripts-operacionais)
- [Documentação](#documentação)

---

## Arquitetura

```
GitHub push → CI (lint + tests) → deploy.yml builda 3 imagens → GHCR
                                                                    ↓
VPS: Watchtower detecta :latest novo → pull → restart automático
       ├── blabla-api         :8000  (FastAPI + Alembic)
       ├── blabla-worker             (Celery worker — 4 filas)
       ├── blabla-beat               (Celery Beat scheduler)
       ├── blabla-dashboard   :3002  (Next.js admin)
       ├── blabla-tecnico-pwa :3003  (Next.js PWA técnico)
       ├── blabla-postgres           (PostgreSQL 16)
       ├── blabla-redis              (Redis 7)
       └── blabla-evolution   :8080  (Evolution API WhatsApp — perfil opcional)
```

Nginx Proxy Manager (ou qualquer reverse proxy) expõe api/dashboard/pwa via HTTPS e repassa para as portas locais.

---

## Stack

| Camada | Tecnologia |
|---|---|
| API | FastAPI + Uvicorn, Python 3.11 |
| Tarefas assíncronas | Celery 5 + Redis (4 filas: default, llm, sgp, notifications) |
| Banco | PostgreSQL 16 (asyncpg + psycopg, particionamento mensal) |
| Cache | Redis 7 |
| Frontend admin | Next.js 15, React 19, shadcn/ui, TanStack Query v5 |
| PWA técnico | Next.js 15, React 19, shadcn/ui, service worker |
| WhatsApp | Evolution API v2 (webhook HMAC + envio via HTTP) |
| LLM | Hermes-3 (compatível OpenAI `/v1/chat/completions`) |
| SGP | Ondeline + LinkNetAM (POST form-encoded, cache Redis+DB) |
| Autenticação | JWT (access 15 min + refresh 7 dias) + CSRF + argon2id |
| Criptografia PII | Fernet (AES-128-CBC) + HMAC-SHA256 com pepper |
| Observabilidade | structlog (PII-masked) + Prometheus `/metrics` + OpenTelemetry + Sentry |
| Imagens | GHCR — 3 imagens, tags `latest` e `sha-{commit}` |
| Deploy contínuo | GitHub Actions → GHCR → Watchtower (pull a cada 30s) |

---

## Deploy em produção (VPS + GHCR)

### Pré-requisitos

- VPS com Docker + Docker Compose v2
- Nginx Proxy Manager (ou Caddy/Nginx) configurado para HTTPS
- Acesso de push ao repositório GitHub

### 1. Configurar secrets no GitHub

**Settings → Secrets and variables → Actions:**

| Secret | Valor |
|---|---|
| `NEXT_PUBLIC_API_URL` | URL pública da API, ex: `https://apiblabla.robertbr.dev` |

O `GITHUB_TOKEN` é automático — o workflow o usa para autenticar no GHCR.

### 2. Autenticar o Docker na VPS com o GHCR

```bash
# Na VPS — use um Personal Access Token com escopo read:packages
echo "SEU_PAT_GHCR" | docker login ghcr.io -u SEU_USUARIO_GITHUB --password-stdin
```

O Watchtower usa o `/root/.docker/config.json` gerado por este comando para fazer pulls automáticos.

### 3. Clonar e configurar o `.env`

```bash
git clone https://github.com/robertbr123/blabla.git
cd blabla/infra

cp .env.example .env
nano .env
```

**Campos obrigatórios:**

```env
POSTGRES_PASSWORD=senha_forte_aqui
JWT_SECRET=string_aleatoria_32_chars_minimo
PII_ENCRYPTION_KEY=chave_fernet_base64_valida
PII_HASH_PEPPER=string_aleatoria_32_chars_minimo
EVOLUTION_KEY=chave_da_evolution_api
EVOLUTION_HMAC_SECRET=secret_do_webhook
GHCR_OWNER=seu_usuario_github
CORS_ORIGINS=https://seudominio.com,https://tecnico.seudominio.com
```

Gerando as chaves:

```bash
# JWT_SECRET e PII_HASH_PEPPER
openssl rand -hex 32

# PII_ENCRYPTION_KEY (formato Fernet)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 4. Subir os serviços

```bash
cd infra

# Puxa as imagens do GHCR e sobe tudo
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# Acompanhe — migrações rodam no startup da API
docker logs blabla-api -f
```

### 5. Criar o primeiro admin

```bash
# Rode a partir da raiz do projeto
ADMIN_EMAIL=admin@seudominio.com \
ADMIN_PASSWORD=senha_forte \
ADMIN_NAME="Administrador" \
bash scripts/seed-admin.sh
```

### 6. Configurar o webhook da Evolution API

No painel da Evolution API, aponte o webhook para:

```
https://apiblabla.seudominio.com/webhook
```

Use o mesmo `EVOLUTION_HMAC_SECRET` configurado no `.env` para assinar as requisições.

### 7. Evolution API local (opcional)

Se quiser rodar a Evolution API no mesmo compose:

```bash
# Adicione ao .env
EVOLUTION_SERVER_URL=https://evolution.seudominio.com

# Suba com o perfil evolution
docker compose -f docker-compose.prod.yml --profile evolution up -d
```

### Deploy contínuo (automático após setup)

Todo push na branch `main`:

1. CI roda lint + 344 testes em paralelo (api, dashboard, pwa)
2. Se CI passar, `deploy.yml` builda as 3 imagens e faz push para o GHCR com tags `:latest` e `:sha-{commit}`
3. O Watchtower na VPS detecta o `:latest` novo em até 30 segundos e reinicia os containers

Nenhuma ação manual na VPS é necessária após o setup inicial.

### Verificar saúde após deploy

```bash
curl https://apiblabla.seudominio.com/livez
curl https://apiblabla.seudominio.com/healthz | python3 -m json.tool

# Smoke test completo
API_BASE=https://apiblabla.seudominio.com bash scripts/smoke-prod.sh
```

### Rollback

```bash
# Opção 1: reverter o commit e fazer push (trigger novo deploy)
git revert HEAD && git push

# Opção 2: puxar um sha específico manualmente na VPS
docker pull ghcr.io/seu_usuario/blabla-api:sha-COMMIT_HASH
cd infra && docker compose -f docker-compose.prod.yml up -d api worker beat
```

---

## Desenvolvimento local

### Requisitos

- Python 3.11+
- Node.js 22+ e pnpm 9+
- Docker + Docker Compose v2

### Setup

```bash
git clone https://github.com/robertbr123/blabla.git
cd blabla

# Copie e edite o .env (valores simples de dev são ok)
cp infra/.env.example infra/.env

# Instale dependências Python
make install

# Instale dependências Node
pnpm install
```

### Subir o ambiente

```bash
make dev       # postgres + redis + api com reload automático
make logs      # acompanha os logs
```

Dashboard e PWA em terminais separados:

```bash
cd apps/dashboard  && pnpm dev   # http://localhost:3000
cd apps/tecnico-pwa && pnpm dev  # http://localhost:3001
```

### Testes e lint

```bash
make test      # pytest (344 testes)
make lint      # ruff + mypy
make format    # ruff format
```

---

## Variáveis de ambiente

Arquivo: `infra/.env` (copiado de `infra/.env.example`).

### Obrigatórias em produção

| Variável | Descrição |
|---|---|
| `POSTGRES_PASSWORD` | Senha do banco |
| `JWT_SECRET` | Segredo JWT (mín. 32 chars) |
| `PII_ENCRYPTION_KEY` | Chave Fernet para criptografar dados PII |
| `PII_HASH_PEPPER` | Pepper HMAC-SHA256 para hashes PII |
| `EVOLUTION_KEY` | API key da Evolution API |
| `EVOLUTION_HMAC_SECRET` | Segredo para validar assinatura do webhook |
| `GHCR_OWNER` | Usuário/org GitHub dono das imagens no GHCR |
| `CORS_ORIGINS` | Origens permitidas separadas por vírgula |

### SGP (Sistema de Gestão de Provedor)

| Variável | Padrão | Descrição |
|---|---|---|
| `SGP_ONDELINE_BASE` | `https://ondeline.sgp.tsmx.com.br` | URL base |
| `SGP_ONDELINE_TOKEN` | _(vazio)_ | Token de autenticação |
| `SGP_ONDELINE_APP` | `mikrotik` | Identificador do app |
| `SGP_LINKNETAM_BASE` | `https://linknetam.sgp.net.br` | URL base |
| `SGP_LINKNETAM_TOKEN` | _(vazio)_ | Token de autenticação |
| `SGP_LINKNETAM_APP` | `APP` | Identificador do app |

> Os tokens também podem ser configurados via dashboard em `/config` — o banco sobrepõe as env vars.  
> Se o token expirar: `docker logs blabla-api 2>&1 | grep sgp.ondeline.http_error`

### Hermes LLM

| Variável | Padrão | Descrição |
|---|---|---|
| `HERMES_URL` | `http://127.0.0.1:8642/v1` | Endpoint compatível OpenAI |
| `HERMES_API_KEY` | _(vazio)_ | API key |
| `HERMES_MODEL` | `Hermes-3` | Identificador do modelo |
| `LLM_MAX_ITER` | `5` | Máximo de iterações por turno |
| `LLM_TIMEOUT_SECONDS` | `30` | Timeout da chamada LLM |

### Observabilidade (opcionais)

| Variável | Descrição |
|---|---|
| `SENTRY_DSN` | DSN do Sentry (vazio = desligado) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Endpoint OTLP HTTP, ex: `http://tempo:4318` |
| `OTEL_SERVICE_NAME` | Nome do serviço nos traces (padrão: `ondeline-api`) |

---

## Serviços Docker

| Container | Imagem | Porta local | Descrição |
|---|---|---|---|
| `blabla-postgres` | postgres:16-alpine | — | Banco de dados (volume persistente) |
| `blabla-redis` | redis:7-alpine | — | Broker Celery + cache SGP (AOF ativo) |
| `blabla-api` | ghcr.io/.../blabla-api | 127.0.0.1:8000 | API FastAPI |
| `blabla-worker` | ghcr.io/.../blabla-api | — | Celery worker (4 filas, concurrency=4) |
| `blabla-beat` | ghcr.io/.../blabla-api | — | Celery Beat (jobs agendados) |
| `blabla-dashboard` | ghcr.io/.../blabla-dashboard | 3002 | Dashboard admin |
| `blabla-tecnico-pwa` | ghcr.io/.../blabla-tecnico-pwa | 3003 | PWA do técnico |
| `blabla-evolution` _(perfil)_ | evoapicloud/evolution-api | 127.0.0.1:8080 | WhatsApp (opcional) |
| `blabla-watchtower` | containrrr/watchtower:1.7.1 | — | Auto-deploy via GHCR (30s) |

---

## Comandos úteis

```bash
# Produção
make prod               # Sobe stack de prod (imagens GHCR)
make prod-down          # Derruba stack de prod
make prod-logs          # Tail dos logs de prod
make prod-worker-logs   # Tail só do worker

# Desenvolvimento
make dev                # Sobe stack de dev
make down               # Derruba stack de dev
make logs               # Tail dos logs de dev

# Manutenção
docker logs blabla-api -f --tail 100
docker exec blabla-redis redis-cli KEYS "sgp:not_found:*"
docker exec blabla-postgres psql -U blabla -d blabla \
  -c "SELECT key, value FROM config WHERE key LIKE 'sgp%';"
```

---

## Banco de dados e migrações

As migrações rodam automaticamente no startup do `blabla-api` via `alembic upgrade head`. Não há downtime — todas as migrações são backward-compatible.

```bash
# Criar nova migração
cd apps/api
alembic revision --autogenerate -m "descricao_da_mudanca"
alembic upgrade head

# Ver histórico
alembic history
```

A tabela `mensagens` é particionada por mês. O Celery Beat cria as partições futuras automaticamente.

---

## Observabilidade

| Endpoint | Código | Descrição |
|---|---|---|
| `GET /livez` | 200 | Liveness — sempre responde se o processo está vivo |
| `GET /healthz` | 200 / 503 | Health completo — 503 se db ou redis estiverem fora |
| `GET /metrics` | 200 | Métricas Prometheus |

**Resposta `/healthz`:**

```json
{
  "status": "ok",
  "checks": {
    "db": "ok",
    "redis": "ok",
    "evolution": "ok"
  },
  "celery": {
    "default": 0, "llm": 0, "sgp": 0, "notifications": 0
  }
}
```

`db` e `redis` são críticos (503 se falharem). `evolution` e filas são informativos.

---

## Scripts operacionais

| Script | Quando usar |
|---|---|
| `scripts/seed-admin.sh` | Criar o primeiro usuário admin (idempotente) |
| `scripts/smoke-prod.sh` | Smoke test pós-deploy (`API_BASE=https://...`) |
| `scripts/check-hermes.sh` | Verificar conectividade com o LLM |
| `scripts/archive-v1.sh` | Arquivar dados do Ondeline v1 (pré-cutover) |
| `infra/pg_dump_local.sh` | Backup local do Postgres (recomendado em cron diário) |

---

## Documentação

| Documento | Conteúdo |
|---|---|
| `infra/.env.example` | Todas as variáveis com descrições |
| `docs/runbooks/cutover.md` | Big-bang v1 → v2 (T-7d → T+7d + rollback) |
| `docs/runbooks/observability.md` | Logs, métricas, traces, Sentry, LGPD |
| `infra/grafana/` | Dashboards Grafana JSON importáveis |
| `docs/superpowers/plans/` | Planos detalhados por milestone (M1–M9) |
