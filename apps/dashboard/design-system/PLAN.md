# Dashboard Redesign Plan

Salvo em 2026-05-20. Plano de melhoria visual/UX da dashboard usando UI-UX-Pro-Max.

## Diagnóstico atual

Dashboard funcional mas genérica — shadcn cru com slate/zinc default, sem identidade BlaBla, sem logo, sidebar plana de 15 itens.

Problemas:
1. Sem identidade — `--primary` é slate-900, igual a qualquer template shadcn. Verde BlaBla do logo não aparece.
2. Logo ausente na sidebar (só texto "BlaBla").
3. Sidebar plana — 15 links sem agrupamento (Atendimento / Operação / Cadastros / Sistema misturados).
4. Topbar quase vazia — só toggle + user menu à direita.
5. Tokens semânticos faltando — sem `--success`, `--warning`, `--info`. OS/leads/manutenções têm status que precisam de cor consistente.
6. Densidade/respiro — `p-6` no main + sidebar `w-60`; itens da nav apertados; sem `max-width` no conteúdo.

## Fase 1 — Design System (fundação)

Rodar `--design-system` com `--persist` para gravar `design-system/MASTER.md`. Saída esperada:
- Paleta semântica derivada do verde do logo (emerald ~#10b981 como primary).
- Tokens novos em `globals.css`: `--primary` virando emerald, `--success`, `--warning`, `--info`, `--danger`.
- Tipografia: Inter já ok; escalas (`text-display`, `text-h1..h3`, `text-body`, `text-caption`) + tabular nums em tabelas/métricas.
- Escala de elevação (sm/md/lg) e radius consistente.

## Fase 2 — Shell (sidebar + topbar + layout)

- **Sidebar**: trocar texto por `logo_horizontal_light.png` / `_dark.png` (Next `<Image>`, troca por tema). Agrupar em seções:
  - *Atendimento*: Conversas, Leads, Indicações
  - *Operação*: OS, Manutenções, Clientes (em campo), Técnicos, Ranking, Produtividade
  - *Cadastros*: Clientes, Planos, Estoque
  - *Sistema*: Canais WhatsApp, Métricas, Configurações
  - Item ativo: barra vertical à esquerda + bg sutil (padrão Linear/Vercel).
- **Topbar**: breadcrumb à esquerda + Command Palette (⌘K) central + notificações + user menu. h-14 → h-12.
- **Main**: `max-w-7xl mx-auto` com escape para páginas que precisam de largura total.

## Fase 3 — Componentes de alto impacto

1. **OS list + detail** — status pills com cor semântica, timeline visual.
2. **Métricas dashboard** — KPI cards com tabular nums, sparklines, charts via `--domain chart`.
3. **Conversas** — revisar densidade, scroll, indicadores de SLA.
4. **Estados vazios** — adicionar em cada lista.

## Fase 4 — Dark mode + a11y pass

Contraste em ambos temas, focus rings visíveis, atalhos no Command Palette.

## Ordem de execução

Fase 1 + 2 num PR só (ganho percebido alto, risco baixo — só tokens + shell). Depois iterar página por página na Fase 3.
