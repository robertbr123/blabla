# BlaBla Dashboard — Design System (Master)

> Source of Truth global. Páginas específicas podem sobrescrever em `design-system/blabla-dashboard/pages/[page].md`.

Promovido em 2026-05-20 a partir do preview em `/design-preview`.

## Pattern: Data-Dense Dashboard

- Padding mínimo, grid eficiente, KPI cards + tabelas + charts
- Filtros sempre visíveis, drill-down via row click
- Mobile: agrupar / esconder colunas secundárias
- Best for: BI, admin, operações, analytics

## Brand

Logo: `apps/tecnico-mobile/assets/branding/logo_horizontal_{light,dark}.png` (compartilhado entre mobile e dashboard).

## Colors (HSL — compatível com shadcn)

### Light

| Token | HSL | Hex aprox | Uso |
|---|---|---|---|
| `--primary` | `160 84% 39%` | `#10B981` emerald-500 | Marca · CTA · item ativo |
| `--primary-foreground` | `0 0% 100%` | `#FFFFFF` | Texto sobre primary |
| `--accent` | `160 84% 96%` | emerald-50 | Hover sutil, item ativo light |
| `--accent-foreground` | `160 84% 25%` | emerald-800 | Texto sobre accent |
| `--success` | `160 84% 39%` | mesmo do primary | Status positivo |
| `--warning` | `38 92% 50%` | `#F59E0B` amber-500 | Atenção, em andamento |
| `--info` | `217 91% 60%` | `#3B82F6` blue-500 | Informativo, aberto |
| `--destructive` | `0 84.2% 60.2%` | `#EF4444` red-500 | Erro, cancelado |
| `--ring` | `160 84% 39%` | emerald | Focus visible |

Base neutra (`--background`, `--foreground`, `--muted`, `--border`) mantida slate — funciona melhor com data-dense.

### Dark

Card sutilmente mais claro que background (`222.2 47% 7%` vs `222.2 84% 4.9%`) pra dar profundidade sem precisar de shadow. Primary fica mais saturado (`160 84% 45%`) pra manter presença.

## Typography — Inter (Minimal Swiss)

Validado pelo plugin: "Minimal Swiss" pairing (Inter only) é o padrão pra dashboards/admin/design systems.

| Token | Size / line / weight | Uso |
|---|---|---|
| display | 30/36 · 700 | Título de página |
| h1 | 24/32 · 600 | Seção principal |
| h2 | 18/28 · 600 | Card title, subsecção |
| h3 | 14/20 · 600 | Label, header de tabela |
| body | 14/20 · 400 | Texto default |
| small | 12/16 · 400 | Caption, helper, badge |

**Tabular nums** aplicado globalmente em `table` e em qualquer elemento com class `.tabular` ou `[data-numeric]` via `globals.css`. KPIs e valores monetários sempre tabular.

## Effects

- Hover row em tabelas: bg `--accent`
- Hover card: `shadow-md` (subtle elevation)
- Transitions: 150-200ms (`ease-out` entering, default para hover)
- Focus ring: 2px emerald com offset-2

## Status pills (a11y · WCAG)

Sempre **ícone + texto**. Cor sozinha NÃO comunica.

| Status OS | Ícone (lucide) | Tone | Token |
|---|---|---|---|
| Aberto | `Clock` | info | blue |
| Em andamento | `PlayCircle` | warning | amber |
| Concluída | `CheckCircle2` | success | emerald |
| Cancelada | `XCircle` | destructive | red |

Visual: bg `tone / 0.12`, text `tone`, ring-inset `tone / 0.3`.

## Spacing & Layout

- Sistema 4/8pt (Tailwind default)
- Container: `max-w-7xl mx-auto` no main (com escape `data-fullbleed` para tabelas largas)
- Sidebar: `w-60` mantido na Fase 2 + agrupamento em seções

## Avoid

- Emojis como ícones → usar `lucide-react`
- Status só com cor → sempre ícone + texto
- Tabelas sem tabular nums → desalinha colunas numéricas
- Hover sem feedback visual
- Animações > 300ms em micro-interações

## Pre-delivery checklist (cada PR de UI)

- [ ] Sem emoji como ícone
- [ ] Hover states com transition 150-200ms
- [ ] Light: texto >=4.5:1
- [ ] Dark: texto >=4.5:1 (testar separado, não inferir do light)
- [ ] Focus visible em todos elementos interativos
- [ ] `prefers-reduced-motion` respeitado
- [ ] Responsivo: 375 / 768 / 1024 / 1440
- [ ] Cursor pointer em elementos clicáveis não-button
- [ ] Status sempre com ícone + texto
- [ ] Valores numéricos com tabular nums

## Próximas fases

- Fase 2 — Shell (sidebar agrupada + logo + topbar com breadcrumb/Cmd+K)
- Fase 3 — Componentes (OS, métricas, conversas, empty states)
- Fase 4 — a11y pass + dark mode review
