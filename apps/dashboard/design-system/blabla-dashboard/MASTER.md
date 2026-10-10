# BlaBla Dashboard — Design System (Master)

> Source of Truth global. Páginas específicas podem sobrescrever em `design-system/blabla-dashboard/pages/[page].md`.

Promovido em 2026-05-20; tema NOC em 2026-10.

## Tema NOC (2026-10) — leia isto primeiro

O dashboard e um console de operacao. **Escuro e o padrao**; o claro continua no
botao da topbar. Tokens em `app/globals.css`, primitivas em
`components/noc/primitives.tsx`, vitrine sem login em `/design-preview`.

### Superficies (do fundo pra frente)

`background` < `sidebar` < `card` < `elevated` (hover de linha, popover). No escuro
nao se usa sombra pra dar profundidade — so a diferenca de superficie + borda.

### Cores com papel fixo

| Papel | Token | Uso |
|---|---|---|
| Marca / acao | `primary` (emerald) | CTA, item ativo, foco |
| Estado bom | `success` | conectado, concluido, fila zerada |
| Atencao | `warning` | aguardando, em andamento, sem tecnico |
| Critico | `destructive` | SLA estourado, falha, cancelado |
| Neutro informativo | `info` | pendente, em atendimento humano |
| Series de grafico | `--chart-1..3` | **so** em marcas de grafico |

Status e reservado pra **estado**: nunca vira "cor da serie 4". Serie de grafico
nunca vira cor de texto. Status sempre com icone/ponto + texto.

### Tipografia

Inter no texto. **JetBrains Mono em todo numero operacional** (classe `.num`):
codigos de OS, telefones, tempos, contagens, datas. Rotulo de secao e cabecalho de
tabela usam `.eyebrow` (caixa alta, 10.5px, espacado). Titulo de pagina: 20px/600.

### Primitivas (use antes de escrever markup novo)

| Componente | Quando |
|---|---|
| `PageHeader` | topo de toda pagina (titulo, descricao, acoes) |
| `Panel` + `PanelHeader` + `PanelBody` | qualquer bloco de conteudo |
| `StatTile` | KPI. `alert` so quando exige acao |
| `StatusDot` / `StatusChip` | estado ao vivo. `pulse` so pra ao vivo ou alerta ativo |
| `FilterTabs` | filtro por status (substitui `<select>` de status) |
| `Avatar`, `Age`, `Skeleton`, `SkeletonRows` | listas |
| `.data-table` | toda tabela (cabecalho, densidade e hover prontos) |
| `Sparkline` | tendencia dentro de um tile |

### Graficos

Um eixo por grafico — medidas de escala diferente viram *small multiples*, nunca
eixo duplo. Linha 2px, area a ~10%, grade hairline solida, crosshair + tooltip no
hover, barra <= 20px com valor fora da ponta. Paleta validada pra daltonismo.

### Movimento

Duas animacoes so: `animate-status-ping` (ponto ao vivo) e `animate-breach`
(linha com SLA estourado). Todo o resto e transicao de cor de 150ms.

## Brand

Logo: `apps/tecnico-mobile/assets/branding/logo_horizontal_{light,dark}.png` (compartilhado entre mobile e dashboard).

## Status pills (a11y · WCAG)

Sempre **ícone + texto**. Cor sozinha NÃO comunica.

| Status OS | Ícone (lucide) | Tone |
|---|---|---|
| Pendente | `Clock` | info |
| Em andamento | `PlayCircle` | warning |
| Concluída | `CheckCircle2` | success |
| Cancelada | `XCircle` | destructive |

Visual: bg `tone / 0.12`, text `tone`, ring-inset `tone / 0.25` (`TONE_SOFT`).

## Spacing & Layout

- Sistema 4/8pt (Tailwind default)
- Container: `max-w-[1600px] mx-auto px-5 py-5` no main, sobre o fundo quadriculado `.noc-canvas`
- Sidebar: `w-60`, superficie `sidebar`, secoes agrupadas, status do sistema no rodape
- Topbar: 48px, breadcrumb + sinais ao vivo (fila, WhatsApp) + relogio

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
