# Build Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar rebuilds lentos da API Docker e hot-reload lento dos frontends Next.js, sem alterar comportamento de produção.

**Architecture:** Dockerfile com uv + layer ordering correto (deps cacheadas separado do código) + volume mount em dev para hot-reload instantâneo + Turbopack nos frontends.

**Tech Stack:** Docker BuildKit, uv (Python package manager), uvicorn --reload, Next.js Turbopack, docker-compose volumes

**Spec:** `docs/superpowers/specs/2026-05-14-build-optimization-design.md`

---

### Task 1: Adicionar `.dockerignore` em `apps/api/`

**Files:**
- Create: `apps/api/.dockerignore`

- [ ] **Step 1: Criar o `.dockerignore`**

Criar o arquivo `apps/api/.dockerignore` com o seguinte conteúdo:

```
.venv/
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/
.ruff_cache/
tests/
conftest.py
alembic/
alembic.ini
*.md
uv.lock
```

> Nota: `uv.lock` será copiado explicitamente pelo Dockerfile, portanto pode ficar no `.dockerignore` para evitar enviá-lo via contexto automático — mas atenção: o Dockerfile precisa copiá-lo com `COPY`. Se preferir, remova `uv.lock` do `.dockerignore` para simplificar.
>
> **Decisão final:** NÃO incluir `uv.lock` no `.dockerignore`, pois o Dockerfile precisa copiá-lo.

Conteúdo correto do arquivo:

```
.venv/
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/
.ruff_cache/
tests/
conftest.py
alembic/
alembic.ini
*.md
```

- [ ] **Step 2: Verificar que o arquivo existe**

```bash
cat apps/api/.dockerignore
```

Esperado: conteúdo do arquivo listado sem erros.

- [ ] **Step 3: Commit**

```bash
git add apps/api/.dockerignore
git commit -m "build: add .dockerignore for api — exclude venv, cache, tests from context"
```

---

### Task 2: Reescrever o Dockerfile com uv + layer ordering correto

**Files:**
- Modify: `apps/api/Dockerfile`

O Dockerfile atual usa `pip` e copia `src/` antes de instalar as deps, invalidando o cache a cada mudança de código. Vamos trocar por `uv` com layers separadas.

- [ ] **Step 1: Substituir o conteúdo do Dockerfile**

Conteúdo completo do novo `apps/api/Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1.7

FROM python:3.11-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libglib2.0-0 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf2.0-0 \
        shared-mime-info \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# uv: gerenciador de pacotes Python muito mais rápido que pip
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN groupadd --system app && useradd --system --gid app --create-home app
WORKDIR /app

# Layer 1: instala só as dependências (cacheada enquanto pyproject.toml/uv.lock não mudam)
COPY --chown=app:app pyproject.toml uv.lock /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# Layer 2: copia o código e instala o pacote (rápido — só o pacote, deps já estão no cache)
COPY --chown=app:app src /app/src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/livez || exit 1

CMD ["uvicorn", "ondeline_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Fazer o build para validar**

```bash
docker build -t ondeline-api-test apps/api/
```

Esperado: build completo sem erros. Na primeira vez vai baixar as deps; na segunda (sem mudar `pyproject.toml`) deve usar o cache e ser muito mais rápido.

- [ ] **Step 3: Verificar que o container inicia (opcional mas recomendado)**

Se postgres/redis já estiverem rodando:
```bash
docker run --rm --network ondeline-v2_default \
  -e DATABASE_URL=postgresql+asyncpg://ondeline:ondeline@postgres:5432/ondeline \
  -e REDIS_URL=redis://redis:6379/0 \
  ondeline-api-test uvicorn ondeline_api.main:app --host 0.0.0.0 --port 8000
```

Ctrl+C para parar. Se não tiver o ambiente de infra rodando, pular este step.

- [ ] **Step 4: Limpar imagem de teste**

```bash
docker rmi ondeline-api-test
```

- [ ] **Step 5: Commit**

```bash
git add apps/api/Dockerfile
git commit -m "build: rewrite Dockerfile with uv + correct layer ordering for cache"
```

---

### Task 3: Configurar hot-reload no docker-compose.dev.yml

**Files:**
- Modify: `infra/docker-compose.dev.yml`

Adicionar volume mount do `src/` no serviço `api` em dev e sobrescrever o command para usar `--reload`. Worker e beat não precisam de hot-reload.

- [ ] **Step 1: Modificar o serviço `api` no docker-compose.dev.yml**

Localizar o serviço `api` (linha ~37) e adicionar `command` e `volumes`:

```yaml
  api:
    build:
      context: ../apps/api
      dockerfile: Dockerfile
    container_name: ondeline-api
    command: ["uvicorn", "ondeline_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    volumes:
      - ../apps/api/src:/app/src
    environment:
      ENV: development
      LOG_LEVEL: INFO
      DATABASE_URL: postgresql+asyncpg://ondeline:ondeline@postgres:5432/ondeline
      DATABASE_URL_SYNC: postgresql+psycopg://ondeline:ondeline@postgres:5432/ondeline
      REDIS_URL: redis://redis:6379/0
    env_file:
      - ../.env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "127.0.0.1:8000:8000"
    restart: unless-stopped
```

> Os serviços `worker` e `beat` continuam sem alteração — usam a imagem cacheada e não precisam de hot-reload.

- [ ] **Step 2: Commit**

```bash
git add infra/docker-compose.dev.yml
git commit -m "build(dev): mount src/ as volume + uvicorn --reload for instant hot-reload"
```

---

### Task 4: Atualizar o Makefile — separar dev de dev-build

**Files:**
- Modify: `Makefile`

Hoje `make dev` sempre passa `--build`, forçando rebuild mesmo quando nada mudou. Vamos separar os dois casos.

- [ ] **Step 1: Atualizar o Makefile**

Conteúdo completo do novo `Makefile`:

```makefile
.PHONY: dev dev-build down test lint logs worker-logs install format

# Sobe os serviços usando imagens cacheadas (não reconstrói)
dev:
	docker compose -f infra/docker-compose.dev.yml --env-file .env up -d

# Força rebuild das imagens antes de subir (use após mudar Dockerfile ou deps)
dev-build:
	docker compose -f infra/docker-compose.dev.yml --env-file .env up -d --build

down:
	docker compose -f infra/docker-compose.dev.yml down

logs:
	docker compose -f infra/docker-compose.dev.yml logs -f

worker-logs:
	docker compose -f infra/docker-compose.dev.yml logs -f worker

install:
	cd apps/api && [ -d .venv ] || python3 -m venv .venv
	cd apps/api && . .venv/bin/activate && pip install -e ".[dev]"

test:
	cd apps/api && . .venv/bin/activate && pytest -v

lint:
	cd apps/api && . .venv/bin/activate && ruff check src tests && mypy src

format:
	cd apps/api && . .venv/bin/activate && ruff format src tests
```

- [ ] **Step 2: Commit**

```bash
git add Makefile
git commit -m "build: separate make dev (cached) from make dev-build (force rebuild)"
```

---

### Task 5: Habilitar Turbopack nos frontends

**Files:**
- Modify: `apps/dashboard/package.json`
- Modify: `apps/tecnico-pwa/package.json`

Next.js 15.1.0 tem Turbopack estável. Adicionar `--turbopack` ao script `dev` reduz cold start e hot-reload em ~5x.

- [ ] **Step 1: Atualizar `apps/dashboard/package.json`**

Linha atual:
```json
"dev": "next dev --port 3000",
```

Nova linha:
```json
"dev": "next dev --turbopack --port 3000",
```

- [ ] **Step 2: Atualizar `apps/tecnico-pwa/package.json`**

Linha atual:
```json
"dev": "next dev --port 3001",
```

Nova linha:
```json
"dev": "next dev --turbopack --port 3001",
```

- [ ] **Step 3: Testar dashboard**

```bash
cd apps/dashboard && pnpm dev
```

Esperado: log de inicialização com `▲ Next.js 15.1.0 (Turbopack)`. Abrir `http://localhost:3000` e confirmar que carrega. Ctrl+C para parar.

- [ ] **Step 4: Testar tecnico-pwa**

```bash
cd apps/tecnico-pwa && pnpm dev
```

Esperado: log com `▲ Next.js 15.1.0 (Turbopack)`. Abrir `http://localhost:3001` e confirmar. Ctrl+C para parar.

- [ ] **Step 5: Commit**

```bash
git add apps/dashboard/package.json apps/tecnico-pwa/package.json
git commit -m "build: enable Turbopack for faster Next.js dev in dashboard and tecnico-pwa"
```

---

### Task 6: Smoke test do fluxo completo

- [ ] **Step 1: Forçar rebuild inicial com o novo Dockerfile**

```bash
make dev-build
```

Esperado: build do Docker com uv (mais rápido que pip). Todos os containers sobem: `ondeline-api`, `ondeline-worker`, `ondeline-beat`, `ondeline-postgres`, `ondeline-redis`.

- [ ] **Step 2: Verificar API respondendo**

```bash
curl -s http://localhost:8000/livez
```

Esperado: `{"status":"ok"}` ou similar (200 OK).

- [ ] **Step 3: Testar hot-reload**

Editar qualquer arquivo `.py` em `apps/api/src/` (ex: adicionar um comentário numa linha qualquer). Observar os logs:

```bash
make logs
```

Esperado em ~1-2s: linha tipo `WARNING:  StatReload detected changes in 'ondeline_api/...' Reloading...` seguida de `Application startup complete.`

- [ ] **Step 4: Testar make dev (sem --build)**

```bash
make down && make dev
```

Esperado: containers sobem em <5s usando imagens cacheadas, sem rebuild.

- [ ] **Step 5: Push final**

```bash
git push origin main
```

---

## Resumo de ganhos esperados

| Situação | Antes | Depois |
|---|---|---|
| Rebuild após mudar código Python | ~2-5 min (pip reinstala tudo) | <5s (só reload uvicorn) |
| Rebuild após mudar deps (pyproject.toml) | ~2-5 min | ~30-60s (uv, com cache) |
| `make dev` (sem mudanças) | ~2-5 min (sempre `--build`) | <5s (usa cache) |
| Next.js cold start | ~15-30s | ~3-8s (Turbopack) |
| Next.js hot-reload | ~3-8s | <1s (Turbopack) |
