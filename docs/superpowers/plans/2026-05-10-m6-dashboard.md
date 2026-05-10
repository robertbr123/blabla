# M6 — Dashboard Admin/Atendente: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Dashboard completo Next.js 15 (App Router + shadcn/ui + TanStack Query) + endpoints REST `/api/v1/*` consumidos por ele. Atendente assume conversas em status=AGUARDANDO, responde, abre/fecha OS, gerencia leads/clientes/técnicos/manutenções/config. Admin vê métricas. SSE para mensagens entrando em tempo real no chat aberto.

**Architecture:** Backend FastAPI com novos routers em `api/v1/*.py`, Pydantic v2 schemas em `api/schemas/`. Pagination cursor-based. SSE via `EventSourceResponse` (sse-starlette ou implementação manual). Frontend mono-app Next.js 15 em `apps/dashboard/` (App Router, RSC server-side onde fizer sentido, client components pra interatividade). Tipos TS gerados via `openapi-typescript` do `/openapi.json`. Auth via cookie HttpOnly já existente do M2.

**Tech Stack Backend:** FastAPI (existente), Pydantic v2 (existente), sse-starlette (NOVA), python-multipart (pra upload de foto OS).
**Tech Stack Frontend:** Next.js 15, React 19, shadcn/ui (Radix + Tailwind 4), TanStack Query v5, openapi-typescript, react-hook-form + zod, lucide-react icons.

**Pré-requisitos:** Tag `m5-notificacoes`, CI verde. Node 20+ + pnpm 9+ disponível.

---

## File Structure

```
apps/api/src/ondeline_api/
├── api/
│   ├── schemas/                 # NEW — Pydantic DTOs
│   │   ├── __init__.py
│   │   ├── pagination.py        # CursorPage[T]
│   │   ├── conversa.py
│   │   ├── mensagem.py
│   │   ├── os.py
│   │   ├── lead.py
│   │   ├── cliente.py
│   │   ├── tecnico.py
│   │   ├── manutencao.py
│   │   ├── config.py
│   │   └── metrica.py
│   ├── v1/                      # NEW — versioned router pkg
│   │   ├── __init__.py
│   │   ├── conversas.py
│   │   ├── conversas_stream.py  # SSE
│   │   ├── ordens_servico.py
│   │   ├── leads.py
│   │   ├── clientes.py
│   │   ├── tecnicos.py
│   │   ├── manutencoes.py
│   │   ├── config.py
│   │   ├── metricas.py
│   │   └── lgpd.py              # export + delete cliente
│   └── deps_v1.py               # NEW — pagination helper, role guards
├── repositories/
│   ├── lead.py                  # NEW
│   ├── cliente.py               # MODIFY (existing) — add list, paginated, search
│   ├── conversa.py              # MODIFY — add list with filters, get_messages
│   └── ordem_servico.py         # MODIFY — add list, update, foto
├── services/
│   ├── conversa_attend.py       # NEW — atendente assume + libera conversa
│   ├── responder.py             # NEW — atendente responde (similar inbound mas role=ATENDENTE)
│   └── conversa_events.py       # NEW — pub/sub via Redis pra SSE
└── workers/
    └── outbound.py              # MODIFY — add atendente_send_message helper

apps/dashboard/                  # NEW — Next.js app
├── package.json
├── next.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.mjs
├── components.json              # shadcn config
├── app/
│   ├── layout.tsx
│   ├── globals.css
│   ├── (auth)/login/page.tsx
│   ├── (admin)/
│   │   ├── layout.tsx           # nav + role guard
│   │   ├── conversas/page.tsx
│   │   ├── conversas/[id]/page.tsx
│   │   ├── os/page.tsx
│   │   ├── os/[id]/page.tsx
│   │   ├── os/nova/page.tsx
│   │   ├── leads/page.tsx
│   │   ├── leads/[id]/page.tsx
│   │   ├── clientes/page.tsx
│   │   ├── tecnicos/page.tsx
│   │   ├── manutencoes/page.tsx
│   │   ├── config/page.tsx
│   │   └── metricas/page.tsx
├── components/
│   ├── ui/                      # shadcn components (button, dialog, table, ...)
│   ├── nav-sidebar.tsx
│   ├── conversa-list.tsx
│   ├── conversa-chat.tsx        # SSE-driven
│   ├── os-table.tsx
│   ├── form-os.tsx
│   └── ...
├── lib/
│   ├── api/
│   │   ├── client.ts            # fetch wrapper com cookie auth
│   │   ├── types.ts             # gerado via openapi-typescript
│   │   └── queries.ts           # TanStack Query hooks
│   ├── auth.ts                  # client-side auth helpers
│   └── utils.ts                 # cn(), date helpers
├── public/
└── .env.example

apps/api/pyproject.toml          # MODIFY — add sse-starlette
infra/docker-compose.dev.yml     # MODIFY — add `dashboard` service (opcional)
.github/workflows/ci.yml         # MODIFY — add frontend job (eslint + tsc + vitest)
pnpm-workspace.yaml              # NEW — root workspace config
```

---

## Pré: Decisões locked

- **Estilo visual:** shadcn/ui defaults (slate). Tema claro+escuro via `next-themes`. Tipografia Inter.
- **Escopo:** Tudo do spec seção 6 (login + conversas + OS + leads + clientes + técnicos + manutenções + config + métricas).
- **Stack:** Next.js 15 (App Router) + shadcn/ui + TanStack Query v5 + react-hook-form + zod.
- **Realtime:** SSE via FastAPI EventSourceResponse + cliente EventSource nativo.
- **Auth:** cookie HttpOnly do M2 reutilizado (sem mudanças). CSRF middleware exempt já cobre `/auth/login` e `/auth/refresh`. Para mutating endpoints v1, CSRF token via header `X-CSRF` (já no middleware do M2).

---

## Tasks

### Task 1: Pagination + base schemas

- Create `api/schemas/__init__.py` and `pagination.py` with `CursorPage[T]` (items, next_cursor) and helper `paginate(query, cursor, limit, key_fn)`.
- Create `api/deps_v1.py` with `require_role(*roles)` (já existe em `auth/rbac.py` — reusa) e `parse_cursor(cursor: str | None) -> datetime | None`.
- Tests: pagination edge cases (first page, last page, empty).

Commit: `feat(m6): add pagination schemas and v1 deps helpers`

### Task 2: /api/v1/conversas (list + detail + messages + atender + responder + encerrar + delete)

- Create `api/schemas/conversa.py` (ConversaOut, ConversaListItem, AtenderIn, ResponderIn, MensagemOut).
- Create `api/v1/conversas.py` with 7 endpoints:
  - `GET /conversas?status=&cidade=&q=&cursor=&limit=`
  - `GET /conversas/{id}` (com últimas 50 mensagens)
  - `GET /conversas/{id}/mensagens?cursor=&limit=`
  - `POST /conversas/{id}/atender` — set atendente_id=current_user, status=HUMANO
  - `POST /conversas/{id}/responder` `{text|media_url}` — atendente envia, persist Mensagem(role=ATENDENTE), enqueue outbound
  - `POST /conversas/{id}/encerrar` — set status=ENCERRADA
  - `DELETE /conversas/{id}` — soft delete (LGPD)
- Modify `repositories/conversa.py`: add `list_paginated(filters, cursor, limit)`, `get_messages(conversa_id, cursor, limit)`.
- Create `services/conversa_attend.py` and `services/responder.py`.
- Modify `workers/outbound.py`: add helper to send message with role override.
- Register router in `main.py`.
- Tests: each endpoint, RBAC (atendente OR admin), pagination.

Commit: `feat(m6): add /api/v1/conversas REST endpoints`

### Task 3: SSE stream para chat

- Add `sse-starlette>=2.1.0` to `pyproject.toml`.
- Create `services/conversa_events.py` with Redis pub/sub: `publish(conversa_id, event)` + `async subscribe(conversa_id) -> AsyncIterator`.
- Modify `services/inbound.py` (or `workers/outbound.py`): após persistir nova mensagem, `await events.publish(conversa_id, {type: "msg", id, role, text, ts})`.
- Create `api/v1/conversas_stream.py` with `GET /conversas/{id}/stream` returning `EventSourceResponse`.
- Tests: publish/subscribe roundtrip, endpoint returns 200 + correct content-type.

Commit: `feat(m6): add SSE stream for live conversation messages`

### Task 4: /api/v1/ordens-servico (list + create + detail + patch + foto + concluir)

- Create `api/schemas/os.py` (OsOut, OsCreate, OsPatch, OsFotoIn).
- Create `api/v1/ordens_servico.py` with 6 endpoints:
  - `GET /os?status=&tecnico=&cidade=&cursor=`
  - `POST /os {cliente_id, problema, endereco, agendamento_at?}`
  - `GET /os/{id}`
  - `PATCH /os/{id} {status?, tecnico_id?, agendamento_at?}`
  - `POST /os/{id}/foto` (multipart + python-multipart)
  - `POST /os/{id}/concluir {csat?, comentario?}`
- Storage de foto: `volumes/os_fotos/<id>/<uuid>.jpg` (chmod 600).
- Modify `repositories/ordem_servico.py`: add `list_paginated`, `update`, `add_foto`.
- Tests + register router.

Commit: `feat(m6): add /api/v1/ordens-servico REST endpoints`

### Task 5: /api/v1/leads (CRUD)

- Schema `lead.py` (LeadOut, LeadIn, LeadPatch).
- Create `repositories/lead.py`.
- `api/v1/leads.py`:
  - `GET /leads?status=&q=&cursor=`
  - `POST /leads`
  - `GET /leads/{id}`
  - `PATCH /leads/{id}`
  - `DELETE /leads/{id}`
- Tests + register.

Commit: `feat(m6): add /api/v1/leads CRUD`

### Task 6: /api/v1/clientes (list + detail + LGPD export + delete)

- Schema `cliente.py` (ClienteOut decrypted, ClienteListItem). PII decrypted ONLY on detail view (not list).
- Modify `repositories/cliente.py`: add `list_paginated(q, cidade, cursor)` + `mark_for_purge(id, days=30)`.
- `api/v1/clientes.py`:
  - `GET /clientes?q=&cidade=&cursor=`
  - `GET /clientes/{id}` (decrypted PII)
  - `GET /clientes/{id}/export` (LGPD: ZIP com tudo)
  - `DELETE /clientes/{id}` (LGPD: soft + retention_until=now+30d)
- Tests + register.

Commit: `feat(m6): add /api/v1/clientes endpoints incl LGPD export/delete`

### Task 7: /api/v1/tecnicos + /api/v1/tecnicos/{id}/areas (CRUD nested)

- Schemas + endpoints:
  - `GET/POST /tecnicos`
  - `GET/PATCH/DELETE /tecnicos/{id}`
  - `GET/POST/DELETE /tecnicos/{id}/areas`
- Tests + register.

Commit: `feat(m6): add /api/v1/tecnicos CRUD with nested areas`

### Task 8: /api/v1/manutencoes (CRUD)

- Schemas + endpoints:
  - `GET /manutencoes?ativas=true`
  - `POST /manutencoes`
  - `GET/PATCH/DELETE /manutencoes/{id}`
- Tests + register.

Commit: `feat(m6): add /api/v1/manutencoes CRUD`

### Task 9: /api/v1/config (k/v) + /api/v1/metricas (dashboard counters)

- Config: `GET /config/{key}`, `PUT /config/{key} {value}` (admin only). Audit via `audit_action` cm.
- Métricas: `GET /metricas` returns `{conversas_aguardando, msgs_24h, os_abertas, tokens_dia, csat_avg_30d, ...}`.
- Tests + register.

Commit: `feat(m6): add /api/v1/config and /api/v1/metricas`

### Task 10: Smoke API completo + push + CI

```bash
make dev
sleep 10
# Test each endpoint group via curl com JWT cookie
# (script smoke em scripts/smoke_v1.sh — opcional)
make test
git push origin main
gh run watch
```

Commit: `chore(m6): mark backend M6 complete`

---

### Task 11: Next.js scaffold + tooling + shadcn init

- Add `pnpm-workspace.yaml` na raiz: `packages: ['apps/*']`.
- Create `apps/dashboard/` via `pnpm create next-app@latest --typescript --tailwind --app --no-src-dir --import-alias "@/*"`.
- `pnpm dlx shadcn@latest init` (slate, neutral, CSS vars, Tailwind v4).
- Install: `@tanstack/react-query`, `react-hook-form`, `zod`, `lucide-react`, `next-themes`, `openapi-typescript --save-dev`.
- Add scripts: `gen:types` (run openapi-typescript against api), `dev`, `build`, `lint`, `typecheck` (`tsc --noEmit`).
- Create `lib/api/client.ts` (fetch wrapper que reusa cookie httpOnly + handle CSRF).
- Create `lib/api/types.ts` placeholder + run `gen:types` first time.
- Create `app/providers.tsx` com QueryClientProvider + ThemeProvider.
- Create `app/layout.tsx` (HTML base + Inter font + providers).

Smoke: `pnpm --filter dashboard dev` boots em :3000.

Commit: `feat(m6): scaffold Next.js dashboard with shadcn/ui + tooling`

### Task 12: Login page + auth context

- `app/(auth)/login/page.tsx` — form react-hook-form + zod, POST `/auth/login`, cookie set automaticamente.
- `lib/auth.ts` — `getCurrentUser()` SSR helper que faz `GET /auth/me` no server.
- Middleware `middleware.ts` — redirect to `/login` if no valid session on `/(admin)/*`.
- Tests Playwright básicos (login flow).

Commit: `feat(m6): add login page and auth middleware`

### Task 13: Admin layout + nav sidebar

- `app/(admin)/layout.tsx` — sidebar nav (lucide icons) + topbar (theme toggle + user menu).
- `components/nav-sidebar.tsx` — links pra todas as páginas com active state.
- Role guard: admin vê tudo, atendente vê só conversas+leads+OS.

Commit: `feat(m6): add admin layout with sidebar nav and role guard`

### Task 14: Conversas list + chat view + SSE

- `app/(admin)/conversas/page.tsx` — table com filtros (status, cidade, busca).
- `app/(admin)/conversas/[id]/page.tsx` — split view: lista de mensagens + composer.
- `components/conversa-chat.tsx` — client component que abre `EventSource('/api/v1/conversas/${id}/stream')`, prepend novas msgs, scroll bottom.
- Botões: Atender (mostra se status=AGUARDANDO), Responder, Encerrar.

Commit: `feat(m6): add conversas list and chat view with SSE realtime`

### Task 15: OS pages (list + detail + create + concluir)

- `app/(admin)/os/page.tsx` — table + filtros.
- `app/(admin)/os/[id]/page.tsx` — detail + foto upload + form concluir.
- `app/(admin)/os/nova/page.tsx` — form create.
- `components/form-os.tsx` — react-hook-form + zod.

Commit: `feat(m6): add OS list/detail/create pages`

### Task 16: Leads + Clientes + Técnicos pages

- `app/(admin)/leads/page.tsx` + `[id]/page.tsx` — CRUD.
- `app/(admin)/clientes/page.tsx` + `[id]/page.tsx` — list + detail (PII shown apenas detail) + botão LGPD export.
- `app/(admin)/tecnicos/page.tsx` — list + criar/editar (nested areas).

Commit: `feat(m6): add leads, clientes, tecnicos pages`

### Task 17: Manutenções + Config + Métricas pages

- `app/(admin)/manutencoes/page.tsx` — calendar/table view + form create.
- `app/(admin)/config/page.tsx` — key/value editor (planos, ack_text, etc.) admin-only.
- `app/(admin)/metricas/page.tsx` — dashboard cards (KPIs do `/api/v1/metricas`) + sparklines (recharts opcional).

Commit: `feat(m6): add manutencoes, config, metricas pages`

### Task 18: CI frontend + smoke + tag

- Modify `.github/workflows/ci.yml` — adicionar job `frontend` que roda `pnpm install --frozen-lockfile && pnpm --filter dashboard run lint && pnpm --filter dashboard run typecheck && pnpm --filter dashboard run build`.
- Smoke manual: full local boot, login, atender uma conversa, criar OS.
- Tag `m6-dashboard`.

Commit: `ci(m6): add frontend CI job + tag m6-dashboard`

---

## DoD

- [ ] 30+ endpoints REST `/api/v1/*` funcionando (conversas, OS, leads, clientes, técnicos, manutenções, config, métricas, LGPD)
- [ ] SSE stream emite eventos quando nova msg chega
- [ ] Pagination cursor-based em todas as listas
- [ ] PII decrypted apenas em detail views (não list)
- [ ] LGPD export ZIP funciona
- [ ] Next.js dashboard boota, login funciona
- [ ] Admin layout + 8+ páginas operacionais
- [ ] Chat realtime via SSE
- [ ] Foto upload OS funciona
- [ ] Tema claro/escuro
- [ ] Tipos TS sincronizados via openapi-typescript
- [ ] CI verde (backend + frontend lint + typecheck + build)
- [ ] Tag `m6-dashboard`

## Notas operacionais

- **PII**: backend decrypted via `decrypt_pii()` no momento da resposta — nunca cache decrypted PII no Redis.
- **Cookie auth + CORS**: dashboard rodando em outro origin (ex: localhost:3000 vs localhost:8000) precisa CORS config + cookie SameSite=Lax (não Strict). Ajustar `cookie_samesite` em `.env` dev.
- **CSRF**: mutating endpoints v1 exigem `X-CSRF` header lido do cookie `csrf_token` (já implementado em M2). Frontend client lê o cookie e attacha o header.
- **Tipos TS**: rodar `pnpm gen:types` após qualquer mudança de schema. Adicionar pre-commit hook opcional.
- **SSE**: requer worker/api configurado pra long-lived connections (uvicorn ok). Em produção atrás de Nginx, configurar `proxy_buffering off` no path `/api/v1/conversas/*/stream`.
