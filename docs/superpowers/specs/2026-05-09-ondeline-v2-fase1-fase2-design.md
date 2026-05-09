# Ondeline v2 — Fase 1 (Estabilização & Segurança) + Fase 2 (Persistência & Concorrência)

**Status:** Approved
**Data:** 2026-05-09
**Autor:** Ondeline Dev (com Claude)
**Escopo:** Reescrita paralela do bot de WhatsApp da Ondeline Telecom + dashboard administrativo + PWA do técnico, substituindo `bot.py`/`dashboard.py` da v1.

---

## 1. Contexto

A v1 do projeto (`/root/BLABLA/ondeline-bot/`) é um MVP funcional do chatbot de atendimento da Ondeline Telecom (provedor de internet brasileiro), composto por:

- `bot.py` (1936 linhas): webhook do Evolution API, FSM de atendimento, integração com SGP (Ondeline e LinkNetAM), Hermes LLM, OS, leads, notificações
- `dashboard.py` (3325 linhas) + HTMLs vanilla: painel administrativo
- Persistência em arquivos JSON soltos
- 14 conversas históricas, 0 OS, 0 notificações no momento do design

A análise prévia identificou riscos críticos: tokens SGP hardcoded em `config.json`, CORS aberto (`*`), webhook sem HMAC, senha SHA-256 sem salt e sem rate-limit, PII (CPF/endereço/faturas) em texto plano sem TTL ou suporte LGPD, estado em RAM (perde no restart), zero testes, log sem rotação (649 KB).

A v2 é uma **reescrita paralela** que nasce com arquitetura limpa, segura e production-ready. O cutover do tráfego do WhatsApp será big-bang com janela de manutenção.

## 2. Decisões fundadoras

| # | Decisão | Escolha |
|---|---|---|
| D1 | Estratégia | Reescrita paralela em `/root/BLABLA/ondeline-v2/` |
| D2 | Tokens SGP | Mantém atuais (já expostos), movidos para `.env`. Rotação posterior. |
| D3 | Banco de dados | PostgreSQL 16 dedicado em Docker (não reaproveita o do Evolution) |
| D4 | Cutover | Big-bang com janela de manutenção (~10 min) |
| D5 | Patches no bot v1 | Nenhum. Foco 100% no v2. |
| D6 | Escopo v2 | Bot + APIs REST + Dashboard Next.js + PWA técnico |
| D7 | Versionamento | git local + GitHub privado (URL a definir) |
| D8 | LLM | Hermes via API OpenAI-compatible com **tool-calling estruturado** |
| D9 | Histórico v1 | Arquivar JSONs em `/root/BLABLA/ondeline-archive/`, banco zerado |
| D10 | RBAC | 3 papéis: admin, atendente, técnico |
| D11 | 2FA | Não na v2 (estrutura preparada, ativação posterior) |
| D12 | Retenção LGPD | 1 ano (auto-purga via job Celery) |
| D13 | Estrutura | Monorepo Python + TypeScript (apps/ + packages/ + infra/) |

## 3. Arquitetura de alto nível

```
┌─────────────────────────────────────────────────────────────────┐
│                    WhatsApp (clientes / técnicos)                │
└──────────────┬──────────────────────────────────┬───────────────┘
               │                                  │
               ▼                                  ▼
        ┌──────────────┐                 ┌──────────────┐
        │ Evolution API│◄────HMAC────────│   ondeline   │
        │  (existente) │                 │   gateway    │
        └──────┬───────┘                 │  (Caddy)     │
               │ webhook                 └──────┬───────┘
               ▼                                 │
        ┌──────────────┐                         │
        │  bot-api     │ ◄───── REST/JSON ───────┤
        │  (FastAPI)   │                         │
        │              │                  ┌──────▼──────┐
        │ • /webhook   │                  │  Next.js    │
        │ • /api/v1/*  │                  │  apps:      │
        │ • OpenAPI    │                  │  • admin    │
        └──┬───┬───┬───┘                  │  • atend.   │
           │   │   │                      │  • tec PWA  │
           │   │   │                      └─────────────┘
           │   │   ▼
           │   │  ┌──────────┐
           │   │  │  Redis   │  ← cache, sessões, fila Celery
           │   │  └──────────┘
           │   ▼
           │  ┌──────────┐
           │  │ Postgres │  ← clientes, OS, conversas (cripto PII)
           │  └──────────┘
           ▼
       ┌──────────┐  ┌──────────┐
       │  Celery  │─▶│  Hermes  │ (LLM com tool-calling)
       │  workers │  │  Gateway │
       │          │  └──────────┘
       │  • SGP   │
       │  • boletos│
       │  • notifs │
       └──────────┘
              │
              ▼
       ┌──────────┐
       │ SGP APIs │ (Ondeline + LinkNetAM)
       └──────────┘
```

### Princípios

- **API-first**: todo backend exposto via OpenAPI; tipos TS gerados automaticamente para os frontends.
- **Stateless**: zero estado em RAM nos processos. Tudo em Postgres/Redis.
- **Idempotente**: deduplicação de mensagens em nível de banco (UNIQUE em `external_id`).
- **Observable**: structlog JSON + métricas Prometheus + traces OpenTelemetry + healthchecks.
- **Async-first**: I/O bloqueante (LLM, SGP, Evolution) sempre em Celery, nunca no request handler.

### Componentes

1. **bot-api (FastAPI)** — webhook + REST. Apenas valida e enfileira; handlers leves.
2. **Celery workers** — processam mensagens, integrações SGP, envio de WhatsApp, notificações. Filas: `default`, `llm`, `sgp`, `notifications`.
3. **Celery beat** — scheduler de jobs recorrentes (aviso vencimento, follow-up OS, purga LGPD, eval LLM).
4. **PostgreSQL 16** — source of truth, criptografia em repouso por campo (Fernet) para PII.
5. **Redis 7** — cache (clientes SGP), sessões/JWT-blacklist, broker Celery, lockout de login.
6. **Next.js 15** — 3 apps (admin, atendente, técnico-PWA). Server Components + shadcn/ui + TanStack Query.
7. **Reverse proxy** — em dev: Caddy embutido no docker-compose com TLS automático. Em prod: o **Nginx Proxy Manager** já existente nas portas 81/443 do host (decisão pragmática para reaproveitar TLS já configurado).

## 4. Estrutura do monorepo

```
ondeline-v2/
├── apps/
│   ├── api/                # FastAPI + Celery (Python 3.11)
│   │   ├── src/ondeline_api/
│   │   │   ├── adapters/    # evolution, sgp, hermes
│   │   │   ├── domain/      # entities, FSM, value objects
│   │   │   ├── services/    # use cases
│   │   │   ├── repositories/# db access
│   │   │   ├── api/         # FastAPI routers (v1/)
│   │   │   ├── workers/     # Celery tasks
│   │   │   └── tools/       # LLM tools
│   │   ├── tests/
│   │   └── pyproject.toml
│   ├── dashboard/          # Next.js 15 (admin + atendente)
│   └── tecnico-pwa/        # Next.js 15 PWA (mobile-first)
├── packages/
│   ├── db/                 # SQLAlchemy + Alembic + crypto helpers
│   └── shared-types/       # tipos TS gerados via openapi-typescript
├── infra/
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   ├── Caddyfile
│   └── prometheus/
├── scripts/
│   ├── archive-v1.sh       # arquiva JSONs antigos
│   ├── seed.py             # dados de dev
│   └── backup.sh           # pg_dump + upload
├── docs/
│   ├── superpowers/specs/  # specs de design
│   ├── ARCHITECTURE.md
│   ├── PRIVACIDADE.md      # política LGPD
│   ├── RUNBOOK.md
│   └── ADRs/
├── .github/workflows/
│   ├── ci.yml
│   └── deploy.yml
├── .env.example
├── .gitignore
├── pyproject.toml          # workspace root
├── pnpm-workspace.yaml
└── README.md
```

## 5. Modelo de dados (Postgres)

### Tabelas

```sql
-- ════════ Identidade ════════
users                    -- admin, atendente, técnico
  id, email, password_hash (argon2id), role, name, whatsapp,
  is_active, last_login_at, created_at, updated_at

sessions                 -- refresh tokens revogáveis
  id, user_id, token_hash, expires_at, ip, user_agent, revoked_at

audit_log                -- toda ação admin (imutável)
  id, user_id, action, resource_type, resource_id,
  before (jsonb), after (jsonb), ip, ts

-- ════════ Negócio ════════
clientes
  id, cpf_cnpj_encrypted, cpf_hash (HMAC-SHA256, indexado),
  nome_encrypted, whatsapp, plano, status,
  endereco_encrypted, cidade,
  sgp_provider (ondeline|linknetam), sgp_id,
  created_at, last_seen_at, retention_until, deleted_at

conversas
  id, cliente_id (nullable, FK), whatsapp,
  estado (FSM enum), atendente_id (FK users, nullable),
  status (bot|aguardando|humano|encerrada),
  created_at, last_message_at, retention_until, deleted_at

mensagens                -- particionada por mês (RANGE no created_at)
  id, conversa_id (FK), external_id (UNIQUE, dedup),
  role (cliente|bot|atendente),
  content_encrypted, media_url, media_type,
  llm_tokens_used (int, nullable),
  llm_tools_called (jsonb, nullable),
  metadata (jsonb), created_at

leads
  id, nome, whatsapp, interesse,
  status (novo|contato|convertido|perdido),
  atendente_id (FK), notas, created_at, updated_at

tecnicos
  id, user_id (FK), nome, whatsapp, ativo,
  gps_last (point), gps_ts

tecnico_areas            -- N:N técnico × área
  tecnico_id (FK), cidade, rua, prioridade
  PRIMARY KEY (tecnico_id, cidade, rua)

ordens_servico
  id, codigo (UNIQUE, OS-YYYYMMDD-NNN),
  cliente_id (FK), tecnico_id (FK, nullable),
  status (pendente|em_andamento|concluida|cancelada),
  problema, endereco, agendamento_at,
  criada_em, concluida_em,
  fotos (jsonb [{url, ts, gps}]), assinatura (text),
  gps_inicio (point), gps_fim (point),
  csat (int 1-5), nps (int -100..100), comentario_cliente

manutencoes
  id, titulo, descricao, inicio_at, fim_at,
  cidades (jsonb [str]), notificar (bool), criada_em

notificacoes
  id, cliente_id (FK), tipo (vencimento|atraso|pagamento|os_concluida),
  agendada_para, enviada_em (nullable),
  status (pendente|enviada|falha|cancelada),
  payload (jsonb), tentativas, created_at

-- ════════ Operacional ════════
sgp_cache                -- cache de respostas SGP
  cpf_hash, provider, payload (jsonb),
  fetched_at, ttl
  PRIMARY KEY (cpf_hash, provider)

llm_eval_samples         -- amostragem para avaliação
  id, conversa_id (FK), prompt, response,
  classification (jsonb), reviewed_by (FK users), reviewed_at

config                   -- substitui config.json
  key (PK), value (jsonb), updated_by (FK), updated_at
```

### FSM de conversa (estado)

`inicio` → `aguarda_opcao` → (`lead_nome` → `lead_interesse`) | (`cliente_cpf` → `cliente`) → `aguarda_atendente` → `humano` → `encerrada`

Transições válidas registradas em `mensagens.metadata.transition`. Estado vive em `conversas.estado`, não em arquivo `_estado.txt`.

### Indexação chave

```sql
CREATE INDEX ix_clientes_cpf_hash ON clientes (cpf_hash) WHERE deleted_at IS NULL;
CREATE INDEX ix_conversas_whatsapp ON conversas (whatsapp) WHERE deleted_at IS NULL;
CREATE INDEX ix_conversas_status ON conversas (status, last_message_at DESC);
CREATE INDEX ix_mensagens_conversa ON mensagens (conversa_id, created_at DESC);
CREATE UNIQUE INDEX ix_mensagens_external ON mensagens (external_id);
CREATE INDEX ix_os_tecnico_status ON ordens_servico (tecnico_id, status);
CREATE INDEX ix_retention ON clientes (retention_until) WHERE deleted_at IS NULL;
```

### Particionamento de mensagens

`mensagens` é particionada por mês (`PARTITION BY RANGE (created_at)`) com retenção automática via job Celery. Padrão `mensagens_YYYY_MM`.

## 6. Surface de API REST (`/api/v1/`)

### Auth
```
POST /auth/login            → {access_token, refresh_token}
POST /auth/refresh          → {access_token}
POST /auth/logout
GET  /auth/me               → user info + role
```

### Conversas (admin/atendente)
```
GET    /conversas?status=&cidade=&q=&cursor=        → paginado
GET    /conversas/{id}
GET    /conversas/{id}/mensagens?cursor=
POST   /conversas/{id}/atender
POST   /conversas/{id}/responder    {text|media}
POST   /conversas/{id}/encerrar
DELETE /conversas/{id}              → soft delete (LGPD)
```

### Ordens de Serviço
```
GET    /os?status=&tecnico=&cidade=
POST   /os                          {cliente_id, problema, endereco, ...}
GET    /os/{id}
PATCH  /os/{id}                     {status, tecnico_id, ...}
POST   /os/{id}/foto                multipart
POST   /os/{id}/concluir            {csat?, comentario_cliente?}
```

### Técnicos (PWA)
```
GET    /tecnico/me/os               → minhas OS abertas
POST   /tecnico/me/gps              {lat, lng}
POST   /tecnico/me/os/{id}/iniciar
POST   /tecnico/me/os/{id}/concluir
```

### Leads, Clientes, Config, Manutenções, Métricas, Audit-log — análogos.

### Webhook (entrada)
```
POST /webhook                       header: X-Hub-Signature-256
```

### LGPD
```
GET    /api/v1/clientes/{id}/export → ZIP com todos os dados (portabilidade)
DELETE /api/v1/clientes/{id}        → direito ao esquecimento (soft + purge agendado)
```

## 7. Tool-calling do LLM

Substitui os parses por regex `[ABRIR_OS]`, `[ENVIAR_BOLETO]`, `[NOTIFICAR_ATENDENTE]` da v1. O LLM recebe via OpenAI-compatible API as tools registradas:

```python
@tool
def buscar_cliente_sgp(cpf_cnpj: str) -> dict:
    """Consulta cliente nos provedores SGP (Ondeline + LinkNetAM)."""

@tool
def enviar_boleto(cliente_id: int, max_boletos: int = 3) -> dict:
    """Envia faturas em aberto via PDF para o WhatsApp do cliente."""

@tool
def abrir_ordem_servico(cliente_id: int, problema: str, endereco: str) -> dict:
    """Cria OS, faz roteamento por cidade/rua, notifica técnico."""

@tool
def transferir_para_humano(motivo: str) -> dict:
    """Marca conversa como aguardando atendente humano."""

@tool
def consultar_planos() -> dict:
    """Retorna planos disponíveis com preços."""

@tool
def consultar_manutencoes(cidade: str) -> dict:
    """Verifica manutenções planejadas afetando uma cidade."""
```

Provider abstraído em `LLMProvider` (interface). Implementação atual: `HermesProvider`. Trocável em config.

## 8. Segurança

### Secrets (`.env`)

```bash
DATABASE_URL=postgresql+asyncpg://ondeline:***@postgres:5432/ondeline
REDIS_URL=redis://redis:6379/0
EVOLUTION_URL=http://localhost:8080
EVOLUTION_KEY=***
EVOLUTION_HMAC_SECRET=***       # validação de webhook
SGP_ONDELINE_TOKEN=***
SGP_LINKNETAM_TOKEN=***
HERMES_URL=http://127.0.0.1:8642/v1
HERMES_API_KEY=***
JWT_SECRET=***
PII_ENCRYPTION_KEY=***          # Fernet (AES-128-CBC + HMAC), 32 bytes
PII_HASH_PEPPER=***             # para cpf_hash
SENTRY_DSN=***
```

`.env.example` versionado com placeholders. `.env` no `.gitignore`. Carregamento via `pydantic-settings`.

### Auth
- Senhas: **Argon2id** (passlib).
- Tokens: JWT access (15min) + refresh (7d) em **cookie HttpOnly + Secure + SameSite=Strict**.
- CSRF: double-submit cookie + header `X-CSRF`.
- RBAC: decorator `@require_role(Role.ADMIN | Role.ATENDENTE)`.
- Login lockout: 5 tentativas em 15min via Redis; bloqueio progressivo.
- Audit: todo login + ação de admin/atendente em `audit_log`.

### Webhook
- HMAC `X-Hub-Signature-256` validado em todo POST `/webhook`.
- Rate limit: 100 req/min por IP (slowapi + Redis).
- Body limit: 1 MB.
- Allowlist de IPs (config opcional).

### Criptografia de PII

| Campo | Estratégia |
|---|---|
| CPF/CNPJ | `cpf_encrypted` (Fernet) + `cpf_hash` (HMAC-SHA256 com pepper) para indexar |
| Nome, endereço | Fernet por campo |
| Conteúdo de mensagem | Fernet por campo |
| Mídia (PDF boleto) | armazenamento em volume com chmod 600 + URL assinada com TTL |
| Conexão DB | TLS |
| Backup | gpg simétrico |

Funções `encrypt_pii()` / `decrypt_pii()` em `packages/db/crypto.py`. Suporte a key versioning para rotação.

### LGPD

- **Auto-purga**: job Celery beat diário deleta registros com `retention_until < now()`.
- **Direito ao esquecimento**: endpoint deleta cliente; mensagens entram em fila de purge em 30 dias (período legal mínimo).
- **Portabilidade**: endpoint `GET /clientes/{id}/export` retorna ZIP com tudo do cliente.
- **Mascaramento de logs**: filtro `MaskPIIFilter` (regex CPF, telefone, email) antes de persistir.
- **Política**: `docs/PRIVACIDADE.md` versionado, link no rodapé do dashboard.

### Hardening operacional

- Containers como `non-root user`.
- Postgres + Redis em rede Docker interna (não expostos no host).
- Em produção: Nginx Proxy Manager existente fornece TLS (Let's Encrypt) + HSTS; aplicação adiciona CSP strict.
- Healthchecks: `/healthz` (DB+Redis ping), `/livez` (ping simples).
- CI: `pip-audit`, `bandit`, `ruff`, `mypy --strict`.

## 9. Observabilidade

| Pilar | Ferramenta | O quê |
|---|---|---|
| Logs | structlog + loguru | JSON, correlation_id, mascaramento PII |
| Métricas | prometheus_client | Latência, tokens LLM/dia, msgs/min, OS abertas, fila Celery |
| Traces | OpenTelemetry → Tempo | webhook → worker → LLM → Evolution |
| Erros | Sentry (opcional) | Tracebacks com breadcrumbs |
| Dashboards | Grafana | KPIs operacionais + KPIs de produto (CSAT, FCR, etc) |

## 10. Deploy

### Dev local
```
docker compose -f infra/docker-compose.dev.yml up
# → postgres + redis + bot-api + worker + beat
# Frontends rodam separadamente:
pnpm --filter dashboard dev
pnpm --filter tecnico-pwa dev
```

### Produção
- `docker-compose.prod.yml`, restart `unless-stopped`.
- Reverse proxy: Nginx Proxy Manager existente (já nas portas 81/443) faz TLS + roteamento por subdomínio. Apenas adicionamos os hosts proxy apontando para os containers do v2.
- Backup diário do Postgres via `pg_dump` + upload (S3/MinIO configurável).
- Logs dos containers com `--log-opt max-size=10m --log-opt max-file=5`.

### Subdomínios sugeridos
- `api.ondeline.<dominio>` → bot-api
- `admin.ondeline.<dominio>` → dashboard admin/atendente
- `tec.ondeline.<dominio>` → PWA técnico

### CI/CD (GitHub Actions)
- **PR**: ruff + mypy --strict + pytest + pip-audit + bandit + frontend (eslint, tsc, vitest).
- **main**: build de imagens → push para `ghcr.io` → deploy via SSH/Coolify.

## 11. Estratégia de testes

| Nível | Stack | Cobertura mínima |
|---|---|---|
| Unit | pytest + freezegun | 80% nas regras de negócio (FSM, parsers, matching técnico) |
| Integração | pytest + testcontainers | Webhook → worker → DB com Postgres+Redis reais |
| Contract | schemathesis sobre OpenAPI | Todos os endpoints |
| Frontend unit | vitest + @testing-library | Componentes críticos |
| E2E | Playwright | Login, atender conversa, criar OS, técnico concluir OS |
| LLM eval | DeepEval / ragas | 50 conversas/dia → LLM-judge |

Definition of Done de cada milestone:
1. Testes unitários + integração passando
2. `mypy --strict` sem erros
3. `ruff` sem warnings
4. Healthcheck verde no container
5. Demonstração funcional via curl ou navegador
6. Commit atômico com mensagem descritiva
7. README do milestone atualizado

## 12. Migração e cutover (big-bang)

```
T-7d  Ambiente staging completo, E2E passando
T-3d  Smoke test em staging com Evolution apontando para staging
T-1d  Backup completo do v1: zip de /root/BLABLA/ondeline-bot/{conversas,ordens_servico,notificacoes,config.json,tecnicos.json}
      → /root/BLABLA/ondeline-archive/v1-snapshot-YYYYMMDD.zip
T-0:
  1. (5min) Aviso de manutenção via WhatsApp para clientes ativos
  2. (1min) Stop bot.py, dashboard.py
  3. (2min) Aponta webhook do Evolution para http://api.ondeline:8000/webhook
  4. (5min) Smoke test: msg de teste do meu WhatsApp → bot v2 responde
  5. Liga monitoramento, plantão por 2h
T+1d  Review de logs, ajustes
T+7d  Limpeza de v1 (mantém zip por 90 dias)
```

### Rollback
Se algo falhar nas primeiras 24h: aponta webhook do Evolution de volta para `http://localhost:8700/webhook`. Restart `bot.py`. Voltou.

## 13. Cronograma (milestones)

| # | Milestone | Tempo | Entregável demonstrável |
|---|---|---|---|
| **M1** | Fundação | ~2 dias | Repo + monorepo + docker-compose sobe Postgres+Redis+API + healthcheck verde + CI básico |
| **M2** | Banco + Auth | ~3 dias | Schema completo + migrações Alembic + auth (login/logout/refresh) + RBAC + audit_log + criptografia PII |
| **M3** | Bot core sem IA | ~4 dias | Webhook HMAC + Celery + FSM + persistência + envio Evolution + dedup. E2E sintéticos. |
| **M4** | SGP + Hermes + tools | ~5 dias | Tools registradas + cache Redis. Bot atende fluxo cliente real ponta a ponta. |
| **M5** | Notificações | ~2 dias | Vencimento/atraso/pagamento/follow-up OS + Celery beat + manutenções |
| **M6** | Dashboard admin/atendente | ~6 dias | Next.js + login + conversas + chat + leads + CRUD técnicos + CRUD OS + config + métricas |
| **M7** | PWA do técnico | ~3 dias | Login + minhas OS + iniciar/concluir + foto + GPS + offline básico |
| **M8** | Observabilidade + LGPD | ~2 dias | Grafana + Prometheus + retenção/purge + export por cliente + Sentry |
| **M9** | Cutover | ~1 dia | Staging → smoke → big-bang → 24h plantão |

**Total: ~28 dias úteis** (≈6 semanas, 1 dev focado).

## 14. Fora de escopo (Phase 4/5 futuras)

Documentado para evitar scope creep:

- RAG sobre base de conhecimento (Phase 4)
- Classificador de intent ML (Phase 4)
- A/B testing de prompts (Phase 4)
- Voice-first (áudio → Whisper → TTS) (Phase 4)
- Predição de churn (Phase 4)
- Multi-canal (Telegram, Instagram, webchat) (Phase 5)
- Multi-tenant (Phase 5)
- 2FA TOTP (Phase 5; estrutura preparada)
- Integrações com Asaas, Mercado Pago, Sigma, IXC, Voalle (Phase 5)
- Marketplace de templates entre provedores (Phase 5)
- App nativo iOS/Android (Phase 5)

## 15. Perguntas em aberto

1. **URL do GitHub privado**: a definir antes de M1 final.
2. **Subdomínios reais**: a definir (depende do registro DNS atual).
3. **Bucket de backup**: S3, MinIO, Backblaze, ou disco local? Decidir antes de M8.
4. **Modelo Hermes default**: confirmar provider/modelo concreto que o gateway está apontando.
5. **Volume esperado de mensagens/dia**: usado para calibrar particionamento e workers.

## 16. Anexos

- v1 snapshot: `/root/BLABLA/ondeline-bot/` (a ser arquivado em `T-1d`).
- Auditoria de segurança da v1: ver Seção 1 deste documento.
- Análise arquitetural completa: gerada em conversa de 2026-05-09 com 3 agentes paralelos.
