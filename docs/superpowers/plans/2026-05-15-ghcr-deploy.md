# GHCR Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Push para `main` → GitHub Actions constrói 3 imagens Docker, publica no GHCR e faz deploy automático no servidor via SSH.

**Architecture:** Workflow `deploy.yml` com dois jobs em série: `build-push` (matrix de 3 apps, buildx com cache GHA) e `deploy` (appleboy/ssh-action). As apps Next.js usam `output: 'standalone'` para imagens mínimas. O `docker-compose.prod.yml` troca `build:` por `image:` e adiciona os serviços dashboard e pwa.

**Tech Stack:** GitHub Actions, Docker Buildx, GHCR (`ghcr.io`), appleboy/ssh-action@v1.0.3, Next.js 15 standalone output, pnpm 9 workspace.

---

## Arquivos

| Ação | Arquivo |
|------|---------|
| Modificar | `apps/dashboard/next.config.ts` |
| Modificar | `apps/tecnico-pwa/next.config.ts` |
| Criar | `apps/dashboard/Dockerfile` |
| Criar | `apps/tecnico-pwa/Dockerfile` |
| Modificar | `infra/docker-compose.prod.yml` |
| Criar | `.github/workflows/deploy.yml` |

---

## Task 1: Habilitar standalone output no dashboard

**Files:**
- Modify: `apps/dashboard/next.config.ts`

- [ ] **Step 1: Editar next.config.ts**

Substituir o conteúdo completo de `apps/dashboard/next.config.ts` por:

```typescript
import path from 'path'
import type { NextConfig } from 'next'

const INTERNAL = process.env.INTERNAL_API_URL
  ?? process.env.NEXT_PUBLIC_API_URL
  ?? 'http://localhost:8000'

const nextConfig: NextConfig = {
  output: 'standalone',
  outputFileTracingRoot: path.join(__dirname, '../../'),
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${INTERNAL}/api/:path*`,
      },
      {
        source: '/auth/:path*',
        destination: `${INTERNAL}/auth/:path*`,
      },
    ]
  },
}

export default nextConfig
```

- [ ] **Step 2: Verificar que o build local ainda funciona**

```bash
cd apps/dashboard && pnpm build
```

Esperado: build termina sem erros, pasta `.next/standalone/` criada.

- [ ] **Step 3: Commit**

```bash
git add apps/dashboard/next.config.ts
git commit -m "feat: enable standalone output for dashboard Docker build"
```

---

## Task 2: Habilitar standalone output no tecnico-pwa

**Files:**
- Modify: `apps/tecnico-pwa/next.config.ts`

- [ ] **Step 1: Editar next.config.ts**

Substituir o conteúdo completo de `apps/tecnico-pwa/next.config.ts` por:

```typescript
import path from 'path'
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',
  outputFileTracingRoot: path.join(__dirname, '../../'),
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'}/api/:path*`,
      },
      {
        source: '/auth/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'}/auth/:path*`,
      },
    ]
  },
}

export default nextConfig
```

- [ ] **Step 2: Verificar build local**

```bash
cd apps/tecnico-pwa && pnpm build
```

Esperado: build termina sem erros, pasta `.next/standalone/` criada.

- [ ] **Step 3: Commit**

```bash
git add apps/tecnico-pwa/next.config.ts
git commit -m "feat: enable standalone output for tecnico-pwa Docker build"
```

---

## Task 3: Dockerfile para o dashboard

**Files:**
- Create: `apps/dashboard/Dockerfile`

- [ ] **Step 1: Criar o Dockerfile**

Criar `apps/dashboard/Dockerfile` com o seguinte conteúdo:

```dockerfile
# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

# ── Dependências ──────────────────────────────────────────────────────────────
FROM base AS deps
WORKDIR /app
COPY pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/dashboard/package.json ./apps/dashboard/
COPY apps/tecnico-pwa/package.json ./apps/tecnico-pwa/
RUN --mount=type=cache,target=/pnpm/store \
    pnpm install --frozen-lockfile

# ── Build ─────────────────────────────────────────────────────────────────────
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/dashboard/node_modules ./apps/dashboard/node_modules
COPY pnpm-workspace.yaml ./
COPY apps/dashboard ./apps/dashboard
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN pnpm --filter=ondeline-dashboard build

# ── Runner ────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
COPY --from=builder /app/apps/dashboard/.next/standalone ./
COPY --from=builder /app/apps/dashboard/.next/static ./apps/dashboard/.next/static
COPY --from=builder /app/apps/dashboard/public ./apps/dashboard/public
EXPOSE 3000
CMD ["node", "apps/dashboard/server.js"]
```

- [ ] **Step 2: Validar build da imagem localmente**

A partir da raiz do monorepo:

```bash
docker build -f apps/dashboard/Dockerfile -t blabla-dashboard:test .
```

Esperado: imagem `blabla-dashboard:test` criada sem erros.

- [ ] **Step 3: Testar container**

```bash
docker run --rm -p 3002:3000 -e NEXT_PUBLIC_API_URL=http://localhost:8000 blabla-dashboard:test
```

Esperado: servidor ouve em `http://localhost:3002`, responde com HTML da página inicial.

- [ ] **Step 4: Commit**

```bash
git add apps/dashboard/Dockerfile
git commit -m "feat: add Dockerfile for dashboard"
```

---

## Task 4: Dockerfile para o tecnico-pwa

**Files:**
- Create: `apps/tecnico-pwa/Dockerfile`

- [ ] **Step 1: Criar o Dockerfile**

Criar `apps/tecnico-pwa/Dockerfile` com o seguinte conteúdo:

```dockerfile
# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

# ── Dependências ──────────────────────────────────────────────────────────────
FROM base AS deps
WORKDIR /app
COPY pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/dashboard/package.json ./apps/dashboard/
COPY apps/tecnico-pwa/package.json ./apps/tecnico-pwa/
RUN --mount=type=cache,target=/pnpm/store \
    pnpm install --frozen-lockfile

# ── Build ─────────────────────────────────────────────────────────────────────
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/tecnico-pwa/node_modules ./apps/tecnico-pwa/node_modules
COPY pnpm-workspace.yaml ./
COPY apps/tecnico-pwa ./apps/tecnico-pwa
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN pnpm --filter=ondeline-tecnico-pwa build

# ── Runner ────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
COPY --from=builder /app/apps/tecnico-pwa/.next/standalone ./
COPY --from=builder /app/apps/tecnico-pwa/.next/static ./apps/tecnico-pwa/.next/static
COPY --from=builder /app/apps/tecnico-pwa/public ./apps/tecnico-pwa/public
EXPOSE 3000
CMD ["node", "apps/tecnico-pwa/server.js"]
```

- [ ] **Step 2: Validar build da imagem**

```bash
docker build -f apps/tecnico-pwa/Dockerfile -t blabla-tecnico-pwa:test .
```

Esperado: imagem `blabla-tecnico-pwa:test` criada sem erros.

- [ ] **Step 3: Testar container**

```bash
docker run --rm -p 3003:3000 -e NEXT_PUBLIC_API_URL=http://localhost:8000 blabla-tecnico-pwa:test
```

Esperado: servidor ouve em `http://localhost:3003`.

- [ ] **Step 4: Commit**

```bash
git add apps/tecnico-pwa/Dockerfile
git commit -m "feat: add Dockerfile for tecnico-pwa"
```

---

## Task 5: Atualizar docker-compose.prod.yml

**Files:**
- Modify: `infra/docker-compose.prod.yml`

- [ ] **Step 1: Substituir `build:` por `image:` nos serviços api/worker/beat e adicionar dashboard e pwa**

O arquivo `infra/docker-compose.prod.yml` precisa de três mudanças:

**a) Serviço `api` — trocar `build:` por `image:`:**
```yaml
  api:
    image: ghcr.io/${GHCR_OWNER}/blabla-api:latest
    container_name: blabla-api
```

**b) Serviço `worker` — trocar `build:` por `image:`:**
```yaml
  worker:
    image: ghcr.io/${GHCR_OWNER}/blabla-api:latest
    container_name: blabla-worker
```

**c) Serviço `beat` — trocar `build:` por `image:`:**
```yaml
  beat:
    image: ghcr.io/${GHCR_OWNER}/blabla-api:latest
    container_name: blabla-beat
```

**d) Adicionar serviço `dashboard` antes de `volumes:`:**
```yaml
  dashboard:
    image: ghcr.io/${GHCR_OWNER}/blabla-dashboard:latest
    container_name: blabla-dashboard
    env_file:
      - ../.env
    ports:
      - "3002:3000"
    depends_on:
      - api
    restart: unless-stopped
    logging: *default-logging

  tecnico-pwa:
    image: ghcr.io/${GHCR_OWNER}/blabla-tecnico-pwa:latest
    container_name: blabla-tecnico-pwa
    env_file:
      - ../.env
    ports:
      - "3003:3000"
    depends_on:
      - api
    restart: unless-stopped
    logging: *default-logging
```

- [ ] **Step 2: Validar sintaxe do compose**

```bash
GHCR_OWNER=test docker compose -f infra/docker-compose.prod.yml config > /dev/null && echo "OK"
```

Esperado: `OK` sem erros.

- [ ] **Step 3: Commit**

```bash
git add infra/docker-compose.prod.yml
git commit -m "feat: switch prod compose to GHCR images and add dashboard/pwa services"
```

---

## Task 6: Criar workflow deploy.yml

**Files:**
- Create: `.github/workflows/deploy.yml`

- [ ] **Step 1: Criar o workflow**

Criar `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]

concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build-push:
    name: Build & push ${{ matrix.app }}
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    strategy:
      matrix:
        include:
          - app: api
            context: apps/api
            dockerfile: apps/api/Dockerfile
            image: blabla-api
          - app: dashboard
            context: .
            dockerfile: apps/dashboard/Dockerfile
            image: blabla-dashboard
          - app: tecnico-pwa
            context: .
            dockerfile: apps/tecnico-pwa/Dockerfile
            image: blabla-tecnico-pwa
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push ${{ matrix.app }}
        uses: docker/build-push-action@v5
        with:
          context: ${{ matrix.context }}
          dockerfile: ${{ matrix.dockerfile }}
          push: true
          tags: |
            ghcr.io/${{ github.repository_owner }}/${{ matrix.image }}:latest
            ghcr.io/${{ github.repository_owner }}/${{ matrix.image }}:sha-${{ github.sha }}
          cache-from: type=gha,scope=${{ matrix.app }}
          cache-to: type=gha,mode=max,scope=${{ matrix.app }}

  deploy:
    name: Deploy to server
    needs: build-push
    runs-on: ubuntu-latest
    steps:
      - name: SSH deploy
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /root/BLABLA/ondeline-v2
            git pull
            docker compose -f infra/docker-compose.prod.yml pull
            docker compose -f infra/docker-compose.prod.yml up -d
```

- [ ] **Step 2: Validar sintaxe YAML**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))" && echo "YAML OK"
```

Esperado: `YAML OK`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "feat: add GitHub Actions deploy workflow with GHCR build and SSH deploy"
```

---

## Task 7: Setup do servidor (one-time)

Esses passos são manuais — executar **uma vez** no servidor destino antes do primeiro deploy automático.

- [ ] **Step 1: Adicionar `GHCR_OWNER` ao `.env` do servidor**

No servidor, editar `/root/BLABLA/ondeline-v2/.env` e adicionar:

```
GHCR_OWNER=<seu-usuario-github>
```

Substitua `<seu-usuario-github>` pelo seu username do GitHub (ex: `joaosilva`).

- [ ] **Step 2: Autenticar Docker no GHCR**

No servidor, gerar um GitHub Personal Access Token com escopo `read:packages` em:
`https://github.com/settings/tokens`

Depois:

```bash
echo "<SEU_TOKEN>" | docker login ghcr.io -u <seu-usuario-github> --password-stdin
```

Esperado: `Login Succeeded`.

- [ ] **Step 3: Adicionar GitHub Secrets no repositório**

Em `https://github.com/<owner>/<repo>/settings/secrets/actions`, criar:

| Secret | Valor |
|--------|-------|
| `SSH_HOST` | IP do servidor (ex: `203.0.113.10`) |
| `SSH_USER` | `root` |
| `SSH_PRIVATE_KEY` | Conteúdo de `~/.ssh/id_rsa` da máquina local |

- [ ] **Step 4: Garantir que a chave pública está no servidor**

Na máquina local:
```bash
ssh-copy-id root@<IP-do-servidor>
```

Ou manualmente adicionar o conteúdo de `~/.ssh/id_rsa.pub` em `/root/.ssh/authorized_keys` no servidor.

- [ ] **Step 5: Verificar SSH funcionando**

```bash
ssh root@<IP-do-servidor> "echo SSH OK"
```

Esperado: `SSH OK`.
