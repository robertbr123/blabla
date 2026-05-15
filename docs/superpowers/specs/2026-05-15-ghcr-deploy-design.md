# Spec: CI/CD com GHCR + Deploy Automático

**Data:** 2026-05-15
**Status:** Aprovado

---

## Objetivo

Todo push na branch `main` deve: construir as imagens Docker das 3 apps, publicar no GitHub Container Registry (GHCR) e fazer deploy automático no servidor via SSH — sem nenhuma ação manual.

---

## Arquitetura

### Fluxo

```
push main
    └─► deploy.yml
            ├─► Job: build-push (3 imagens em paralelo)
            │       ├── ghcr.io/<owner>/blabla-api:latest + :<sha>
            │       ├── ghcr.io/<owner>/blabla-dashboard:latest + :<sha>
            │       └── ghcr.io/<owner>/blabla-tecnico-pwa:latest + :<sha>
            │
            └─► Job: deploy (depende de build-push)
                    └── SSH no servidor
                        cd /root/BLABLA/ondeline-v2
                        git pull
                        docker compose -f infra/docker-compose.prod.yml pull
                        docker compose -f infra/docker-compose.prod.yml up -d
```

O `ci.yml` existente continua rodando em paralelo (lint + testes). O `deploy.yml` é independente — não bloqueia nem depende do CI.

---

## Componentes

### 1. `apps/dashboard/Dockerfile` (novo)

Multi-stage Next.js 15:
- Stage `deps`: instala dependências com pnpm
- Stage `builder`: roda `pnpm build` com `NEXT_PUBLIC_API_URL` como build arg
- Stage `runner`: imagem node slim, copia `.next` e `node_modules`, expõe porta 3002

### 2. `apps/tecnico-pwa/Dockerfile` (novo)

Idêntico ao dashboard, porta 3003.

### 3. `.github/workflows/deploy.yml` (novo)

- **Trigger:** `push` na branch `main`
- **Job `build-push`:**
  - Login GHCR com `GITHUB_TOKEN` (automático, sem secret extra)
  - Docker buildx para cache eficiente
  - Build e push das 3 imagens com tags `latest` e `sha-<hash>`
- **Job `deploy`:** depende de `build-push`
  - SSH via `appleboy/ssh-action`
  - `git pull` + `docker compose pull` + `docker compose up -d`

### 4. `infra/docker-compose.prod.yml` (alterado)

- `api`, `worker`, `beat`: substituir `build:` por `image: ghcr.io/$GHCR_OWNER/blabla-api:latest`
- Adicionar serviço `dashboard`: imagem GHCR, porta `3002:3000`, `env_file: ../.env`
- Adicionar serviço `tecnico-pwa`: imagem GHCR, porta `3003:3000`, `env_file: ../.env`
- `GHCR_OWNER` definido via variável de ambiente ou hardcoded no compose

---

## GitHub Secrets necessários

| Secret | Valor |
|---|---|
| `SSH_HOST` | IP ou domínio do servidor |
| `SSH_USER` | Usuário SSH (ex: `root`) |
| `SSH_PRIVATE_KEY` | Chave privada SSH (conteúdo do `~/.ssh/id_rsa`) |

GHCR usa `GITHUB_TOKEN` automático — nenhum secret adicional.

---

## Variáveis de ambiente das imagens Next.js

- `NEXT_PUBLIC_API_URL` — URL pública da API (necessária em build time para o browser)
- `INTERNAL_API_URL` — URL interna da API (server-side, ex: `http://blabla-api:8000`)

No container em produção, o `INTERNAL_API_URL` aponta para o serviço `api` na rede Docker. O `env_file: ../.env` injeta ambas.

---

## Critérios de sucesso

- Push no `main` → imagens publicadas no GHCR com tag `latest` e `sha-<hash>`
- Servidor atualizado automaticamente sem intervenção manual
- Em uma máquina nova com Docker: `docker compose pull && docker compose up -d` sobe todo o sistema
- Portas 3002 (dashboard) e 3003 (tecnico-pwa) acessíveis no servidor
