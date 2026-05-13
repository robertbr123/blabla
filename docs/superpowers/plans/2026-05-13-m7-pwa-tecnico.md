# M7 — PWA Técnico: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** PWA mobile-first para o técnico em campo: lista de OS atribuídas, iniciar/concluir OS, capturar GPS, upload de foto via câmera nativa. Login reusando JWT do M2 (role=tecnico). App-shell offline (service worker cacheia HTML/JS/CSS — dados precisam de rede).

**Architecture:** App separado em `apps/tecnico-pwa/` (Next.js 15 App Router) com manifest.json + service worker simples (cache-first pra app shell). Backend adiciona 4 endpoints `/api/v1/tecnico/me/*`. Captura de foto via `<input type="file" capture="environment">`. GPS via `navigator.geolocation`.

**Tech Stack:** Next.js 15, React 19, shadcn/ui (componentes copiados do dashboard), TanStack Query v5. Service worker manual (sem next-pwa para manter simples).

**Pré-requisitos:** Tag `m6-dashboard`, CI verde.

---

## File Structure

```
apps/api/src/ondeline_api/
├── api/schemas/
│   └── tecnico_me.py            # NEW — DTOs (MyOsListItem, GpsUpdate, IniciarIn, ConcluirIn)
├── api/v1/
│   └── tecnico_me.py            # NEW — 4 endpoints
└── repositories/
    ├── ordem_servico.py         # MODIFY — add list_for_tecnico, set_iniciada/concluida_with_gps
    └── tecnico.py               # MODIFY — add update_gps, get_by_user_id

apps/tecnico-pwa/                # NEW — Next.js app
├── package.json
├── next.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.mjs
├── components.json
├── .eslintrc.json
├── .env.example
├── public/
│   ├── manifest.json
│   ├── sw.js                   # service worker
│   ├── icon-192.png            # placeholder
│   └── icon-512.png            # placeholder
├── app/
│   ├── layout.tsx              # mobile viewport + manifest link + sw register
│   ├── globals.css
│   ├── providers.tsx
│   ├── (auth)/login/page.tsx
│   ├── (tec)/
│   │   ├── layout.tsx          # auth check role=tecnico
│   │   ├── page.tsx            # lista de minhas OS
│   │   └── os/[id]/page.tsx    # detail + iniciar/concluir/foto/gps
├── components/
│   ├── ui/                     # shadcn (Button, Card, Input, Label, Badge)
│   ├── os-card.tsx             # mobile OS card list item
│   ├── os-action-bar.tsx       # iniciar/concluir CTAs
│   └── gps-button.tsx          # captura GPS + envia
├── lib/
│   ├── api/
│   │   ├── client.ts
│   │   ├── types.ts
│   │   └── queries.ts
│   ├── auth.ts
│   └── utils.ts
└── middleware.ts               # role guard

.github/workflows/ci.yml         # MODIFY — add pwa job (paralelo)
pnpm-workspace.yaml              # NO-OP (apps/* já cobre)
```

---

## Tasks

### Task 1: Backend — schemas + repos extensions + 4 endpoints `/api/v1/tecnico/me/*`

Endpoints (todos com `Role.TECNICO` only):
1. `GET /api/v1/tecnico/me/os` — minhas OS (atribuídas e não concluídas)
2. `POST /api/v1/tecnico/me/gps` body `{lat, lng}` — atualiza Tecnico.gps_lat/lng/ts
3. `POST /api/v1/tecnico/me/os/{id}/iniciar` — `OsStatus.EM_ANDAMENTO` + `gps_inicio_lat/lng`
4. `POST /api/v1/tecnico/me/os/{id}/concluir` body `{csat?, comentario?, lat?, lng?}` — `CONCLUIDA` + `concluida_em` + `gps_fim_lat/lng` + `csat`

Helper: `current_tecnico` dep que carrega `Tecnico` por `user_id` (via JWT current_user). 401 se user não tem técnico associado.

Tests (~8): GET filtered to my OS; iniciar sets em_andamento; concluir sets concluida + csat + GPS; cannot iniciar/concluir other tecnico's OS (403); GPS update succeeds.

Commit: `feat(m7): add /api/v1/tecnico/me/* endpoints`

### Task 2: PWA scaffold (Next.js 15 + Tailwind + shadcn)

Mirror `apps/dashboard` setup but mobile-first.

- `apps/tecnico-pwa/package.json` (mesmas deps + sem `@radix-ui/react-select` — usa native)
- Configs (next, ts, tailwind, postcss, components.json, eslint)
- `app/globals.css` — mesmo tema slate
- `app/layout.tsx`:
  - viewport: `width=device-width, initial-scale=1, maximum-scale=1`
  - `<link rel="manifest" href="/manifest.json">`
  - script tag inline registrando `/sw.js`
  - `<meta name="theme-color" content="#020817">`
- `app/providers.tsx` (TanStack Query + ThemeProvider)
- `app/page.tsx` redirects to `/login` or `/` based on auth
- `lib/utils.ts`, `lib/api/client.ts`, `lib/api/types.ts`, `lib/auth.ts` (mesmo do dashboard)
- `components/ui/` — copiar Button, Card, Input, Label, Badge do dashboard
- `public/manifest.json`:
  ```json
  {
    "name": "Ondeline Técnico",
    "short_name": "Ondeline Téc",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#020817",
    "theme_color": "#020817",
    "icons": [
      {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
      {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}
    ]
  }
  ```
- `public/sw.js` — minimal cache-first service worker:
  ```javascript
  const CACHE = 'tecnico-pwa-v1'
  const APP_SHELL = ['/']
  self.addEventListener('install', (e) => {
    e.waitUntil(caches.open(CACHE).then((c) => c.addAll(APP_SHELL)))
    self.skipWaiting()
  })
  self.addEventListener('activate', (e) => {
    e.waitUntil(caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ))
    self.clients.claim()
  })
  self.addEventListener('fetch', (e) => {
    const req = e.request
    if (req.method !== 'GET') return
    const url = new URL(req.url)
    // Don't cache API or auth — always go to network
    if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/auth/')) return
    e.respondWith(
      caches.match(req).then((cached) =>
        cached || fetch(req).then((res) => {
          if (res.ok && res.type === 'basic') {
            const copy = res.clone()
            caches.open(CACHE).then((c) => c.put(req, copy))
          }
          return res
        }).catch(() => cached)
      )
    )
  })
  ```
- Placeholder PNG icons: just create 1x1 transparent PNGs at `public/icon-192.png` and `public/icon-512.png` (real icons can be added later).
- `next.config.ts` with rewrites para `/api/*` → backend.
- `middleware.ts` (gate `/` and `/os/*` by `refresh_token` cookie + redirect to /login).
- `.env.example` com `NEXT_PUBLIC_API_URL=http://localhost:8000`.

Smoke: install + typecheck + lint + build.

Commit: `feat(m7): scaffold tecnico PWA app shell + service worker`

### Task 3: Login + auth + lista de OS (home)

- `app/(auth)/login/page.tsx` — mesmo padrão do dashboard mas mobile-first (form maior, botão full-width).
- `app/(tec)/layout.tsx` — verifica `getMeServer()`, redireciona se não for `tecnico`. Topbar mínima (logo + logout button).
- `app/(tec)/page.tsx` — lista de minhas OS via `useMyOs()` hook. Cards mobile-friendly.
- `components/os-card.tsx` — Card com codigo, status badge, problema (truncado), endereço, link para detail.
- `lib/api/queries.ts` — `useMyOs()`, `useUpdateGps()`, `useIniciarOs()`, `useConcluirOs()`.

Commit: `feat(m7): add tecnico login + my OS list`

### Task 4: OS detail mobile-first + iniciar + concluir + GPS + foto

- `app/(tec)/os/[id]/page.tsx` — usa o mesmo endpoint público `/api/v1/os/{id}` (técnico tem permissão? Talvez não — usar `/api/v1/tecnico/me/os/{id}` se necessário, ou ajustar role gate). **Decisão:** endpoint público `/api/v1/os/{id}` requer ATENDENTE/ADMIN — NÃO funciona pra técnico. Adicionar `Role.TECNICO` ao `_role_dep` do `ordens_servico.py` GET endpoints OU criar `/api/v1/tecnico/me/os/{id}` específico (preferred — autorização precisa garantir que tecnico só vê SUAS OS).

  → Adicionar `GET /api/v1/tecnico/me/os/{id}` no Task 1 (revisar e adicionar 5º endpoint).
- `components/os-action-bar.tsx`:
  - Se `status=pendente`: botão "Iniciar OS" (pede GPS, chama iniciar)
  - Se `status=em_andamento`: botões "Adicionar foto" (input file capture) + "Concluir" (com form CSAT inline)
  - Se `status=concluida`: read-only com fotos + CSAT
- `components/gps-button.tsx` — wrapper do `navigator.geolocation.getCurrentPosition` com timeout + erro UX.
- Foto upload reutiliza `useUploadFoto` (do M6 — adaptar para pegar do dashboard).

Commit: `feat(m7): add tecnico OS detail with iniciar, concluir, GPS, foto`

### Task 5: CI + smoke + tag

- `.github/workflows/ci.yml` — adicionar job `pwa` (paralelo ao `frontend`):
  ```yaml
    pwa:
      name: tecnico-pwa (lint + typecheck + build)
      runs-on: ubuntu-latest
      defaults:
        run:
          working-directory: apps/tecnico-pwa
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-node@v4
          with: { node-version: '22' }
        - run: corepack enable && corepack prepare pnpm@9.15.0 --activate
        - uses: actions/cache@v4
          with:
            path: ~/.local/share/pnpm/store
            key: pnpm-${{ runner.os }}-${{ hashFiles('pnpm-lock.yaml') }}
        - working-directory: .
          run: pnpm install --frozen-lockfile
        - run: pnpm lint
        - run: pnpm typecheck
        - run: pnpm build
          env:
            NEXT_PUBLIC_API_URL: http://localhost:8000
  ```
- Smoke local: full suite + dashboard build + pwa build.
- Push, watch CI all 3 jobs green.
- Tag `m7-pwa-tecnico`.

Commit: `ci(m7): add pwa CI job + tag m7-pwa-tecnico`

---

## DoD

- [ ] 5 endpoints `/api/v1/tecnico/me/*` (list OS, get OS, GPS update, iniciar, concluir)
- [ ] PWA app boota standalone com manifest + service worker
- [ ] Login funciona, role guard restringe a TECNICO
- [ ] Lista de OS atribuídas
- [ ] Detail com iniciar (com GPS) + concluir (com GPS + CSAT) + foto upload (câmera nativa)
- [ ] App shell cacheado offline (testável: load app → desliga rede → recarrega → app abre)
- [ ] Backend + dashboard + pwa CI todos verde
- [ ] Tag `m7-pwa-tecnico`
