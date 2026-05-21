# BlaBla Mobile — Mega Redesign Plan

Data: 2026-05-21 · Alvo: alinhar tecnico-mobile com a identidade do dashboard (verde BlaBla, tokens semânticos, padrões "Data-Dense Dashboard" do UI/UX Pro Max) e enxugar telas que ficaram inchadas.

---

## Diagnóstico — o que está errado hoje

### Cores fora de marca
`lib/core/theme.dart`:
- `brandCommand = #17324D` (navy escuro) ← primary atual
- `brandAccent = #C18A2D` (mustard) ← secondary atual
- `brandWarm = #F6F1E8` (creme) ← background "cosy"

Nenhuma dessas bate com o logo BlaBla (verde emerald `#10B981`) nem com o dashboard. O app parece de outro produto.

### Estoque inchado
`lib/features/estoque/estoque_screen.dart:74` — um único `AppSurfaceCard` gigante no topo carrega:
- SectionHeader com subtítulo de 2 linhas
- 3 status chips quebrando linha
- 2 KPI cards lado a lado
- Search field
- FilterChip + contador

Resultado: ~280px ocupados antes do primeiro item da lista. Empilhado, abafado.

### Perfil pesado
`perfil_screen.dart` com 869 linhas. Provavelmente muitas seções uma seguida da outra sem hierarquia visual clara.

### Falta padronização
- KPIs em telas diferentes usam estruturas diferentes (`_Resumo` em estoque é local, sem reuso)
- Status chip já existe (`AppStatusChip`) mas convive com Chips Material genéricos em outros lugares
- Não há `EmptyState` global (cada tela monta o seu)

### Vínculo com dashboard
Os técnicos vão receber notificações e ver telas que vieram do mesmo backend. Não faz sentido o app mobile ter linguagem visual completamente diferente do dashboard que o supervisor usa. O **logo BlaBla é verde**, então o verde é a marca — não o navy.

---

## Goal — design system unificado

Mesmos princípios do dashboard, traduzidos para Flutter/Material 3:

| Token (Flutter) | Valor | Hex | Uso |
|---|---|---|---|
| `brandPrimary` | emerald-500 | `#10B981` | Marca, botões CTA, indicador ativo bottom nav |
| `brandPrimaryDark` | emerald-600 | `#059669` | Pressed state, dark-mode primary |
| `brandSuccess` | mesmo do primary | `#10B981` | OS concluída, "tudo certo" |
| `brandWarning` | amber-500 | `#F59E0B` | Em andamento, atenção |
| `brandInfo` | blue-500 | `#3B82F6` | Pendente, informativo |
| `brandDanger` | red-500 | `#EF4444` | Erro, cancelar |
| Neutro base | slate | `#0F172A` / `#F8FAFC` | Texto e fundo (não creme) |

Tipografia: **Inter** (mesma do dashboard) via google_fonts. Pesos 400/500/600/700. Escala explícita:

| Token | Size / line / weight | Uso |
|---|---|---|
| `displayTitle` | 28/34 · 700 | AppBar large, header de tela |
| `sectionTitle` | 18/24 · 600 | Section header dentro da tela |
| `cardTitle` | 16/22 · 600 | Título de card/list tile |
| `body` | 14/20 · 400 | Default |
| `bodyEmphasis` | 14/20 · 500 | Label "STATUS" etc |
| `caption` | 12/16 · 400 | Metadata, timestamp |
| `numeric` | 14-32 · tabular | Valores monetários, contadores, coordenadas |

Forma: radius **12** para cards (médio), **8** para chips/badges, **999** para pills.
Elevação: shadow **xs** (cards), **md** (modais).

---

## Componentes a criar/refinar

### Novos (drop-in everywhere)

1. **`BrandStatusPill`** — equivalente do `OsStatusPill` da web. Ícone + label + tonal bg (success/warning/info/destructive/neutral). 2 sizes (sm/md). Substitui `AppStatusChip` e Material `Chip` em status.

2. **`BrandKpiCard`** — KPI compacto: label uppercase 11px, valor 28px tabular-nums, ícone 16px num quadrado tintado 36×36. Tone configurable. Substitui `_Resumo` local de estoque.

3. **`BrandEmptyState`** — ícone 40px (muted), title 14px medium, description 12px muted, optional action. Mesmo padrão do dashboard.

4. **`BrandSection`** — substitui `AppSectionHeader` com hierarquia mais clara (título sem subtítulo abaixo de tudo; spacing 24 antes / 12 depois).

5. **`BrandListTile`** — linha de lista com avatar/ícone à esquerda, título + subtítulo, status pill à direita. Pra listas de OS, Cliente, Estoque.

### Refinar

- `AppSurfaceCard` → manter, ajustar radius=12 e remover o shadow muito pesado.
- Bottom nav: 4 tabs com label + ícone, indicador verde por trás do ativo (Material 3 NavigationBar).

---

## Fases

### Fase 1 · Foundations (cores + tipografia + tokens semânticos)

**Risco:** alto se feito mal. Toca TODAS as telas.
**Mitigação:** rodar uma tela de cada vez no preview antes de promover.

Entregáveis:
- Reescrever `lib/core/theme.dart`: ColorScheme com primary emerald, semantic colors expostos como extension (`Theme.of(context).extension<BrandTokens>()!.success` etc).
- Criar `lib/core/branding/brand_tokens.dart` — `ThemeExtension<BrandTokens>` com success/warning/info/danger + tonal variants.
- Trocar todas referências a `brandCommand`/`brandAccent`/`brandWarm` por tokens do scheme/extension. Os aliases `brandGreen/brandInk/brandCream` já viraram emerald — só remover.
- Adicionar `google_fonts` no pubspec, aplicar Inter no `textTheme`.
- Tabular nums via `TextStyle(fontFeatures: [FontFeature.tabularFigures()])` num helper.

### Fase 2 · Shell + Login

**Risco:** baixo. Mexe na primeira impressão.

- Login: logo BlaBla centralizado + glow emerald sutil de fundo (replicar a dashboard `/login`). Botão "Entrar" emerald. Toggle show/hide senha (Material 3 já tem). `prefers-reduced-motion` respeitado.
- Bottom nav: trocar BottomNavigationBar legado por `NavigationBar` Material 3, indicador emerald `selectedIndex`, ícones outlined→filled no selected.

### Fase 3 · Componentes core (drop-in)

Implementar os 5 componentes novos (`BrandStatusPill`, `BrandKpiCard`, `BrandEmptyState`, `BrandSection`, `BrandListTile`).
Substituir uso de `AppStatusChip` por `BrandStatusPill` em todo o app (grep + replace).
Cada componente com goldens/widget tests pra travar contrato visual.

### Fase 4 · Estoque (problema do "card grande")

Estrutura nova:
```
AppBar "Estoque" + ações (refresh)
├── Strip de KPIs (3 BrandKpiCard em Row, scrollable horizontal se não couber)
│   • Itens em estoque (totalItens) — primary
│   • Categorias (categorias) — info
│   • Filtro ativo (Todos / Com saldo) — neutral
├── SearchBar full-width (sem padding extra, isDense)
│   └── Trailing: FilterChip "Apenas com saldo"
├── Counter linha: "X de Y itens visíveis"
└── Lista de items (já existe — só padronizar com BrandListTile)
```

Ganho: ~120px liberados no topo. Hierarquia mais clara (KPIs visualmente separados dos filtros).

### Fase 5 · Clientes (lista + detalhe + novo)

- Lista: BrandListTile com avatar (initials gerada), endereço resumido, status SGP como BrandStatusPill à direita.
- Detalhe: header com avatar grande + nome + CPF + status SGP. Tabs ou seções (Plano / Endereço / Instalação / Fotos / Materiais).
- Novo: formulário em steps (Wizard 3 steps: identidade → endereço → instalação) ao invés de 1 form gigante — diminui ansiedade do técnico em campo.

### Fase 6 · OS (lista + detalhe)

- Lista: BrandListTile com código mono, nome cliente, BrandStatusPill (Pendente/Em andamento/Concluída/Cancelada), distância (se GPS), botão "Iniciar" inline quando aplicável.
- Detalhe: header sticky com código + status. Conteúdo organizado em seções colapsáveis quando concluída (Diagnóstico / Materiais / Fotos / CSAT).

### Fase 7 · Perfil

Hoje: 869 linhas, sem hierarquia.

Plano:
- Header BrandHeader: avatar 80px + nome + role pill (técnico)
- Seções verticais bem espaçadas:
  - Conta (nome, email — read-only display)
  - Estatísticas do mês (OS concluídas, CSAT médio, materiais usados) — usar BrandKpiCard
  - Notificações (toggle FCM)
  - Aparência (light / dark / system)
  - Sair (botão danger no final, com confirm dialog)

Cortar tudo que não usar. Meta: < 350 linhas.

### Fase 8 · Polish + dark mode

- Auditar contraste em ambos os modos (testar com simulador).
- Splash screen com logo + spinner emerald.
- Snackbars tonalmente coloridos (success verde sutil, error vermelho sutil).
- Padronizar animações: 200ms ease-out (entering), 150ms ease-in (exiting). Respeitar `MediaQuery.disableAnimations`.

---

## Ordem de execução recomendada

1. **Fase 1** num PR só — fundação. Build local + testar 1 tela de cada feature pra ver se nada quebrou.
2. **Fase 3** componentes em outro PR — não toca telas, só cria primitivos.
3. **Fase 2** (login + shell) — primeira impressão.
4. **Fase 4** Estoque — você já apontou o problema.
5. **Fase 7** Perfil — maior cleanup.
6. **Fases 5 e 6** (Clientes / OS) — telas mais usadas, deixar por último com componentes maduros.
7. **Fase 8** polish.

---

## O que está bom — manter

- Arquitetura: feature folders + riverpod + go_router. Mantemos.
- `app_surfaces.dart`, `app_status_chip.dart`, `app_section_header.dart` — bases sólidas, só renomear/refinar.
- Cliente form com offline outbox — não mexer na lógica, só visual.
- OS Iniciar/Concluir com GPS e câmera — não mexer.
- FCM + auth biométrica — não mexer.

---

## Risco geral

- Material 3 NavigationBar é diferente de BottomNavigationBar — vale double-check em iOS pra confirmar não dá glitch.
- Mudar primary color afeta toda hover state, ripple, focus ring — testar com slow-mo no emulador.
- Inter via google_fonts faz download na primeira vez. Considerar `GoogleFonts.config.allowRuntimeFetching = false` + bundling local pra evitar delay.

---

## Próximo passo

Aprova esse plano? Se sim:
1. Começo pela **Fase 1** com preview num route temporário `/design-preview` (igual fiz no dashboard) — você vê os tokens novos sem afetar nenhuma tela real.
2. Aprovado o preview, promovo pro `theme.dart` global.
3. Aí seguimos fase por fase, sem pressa.
