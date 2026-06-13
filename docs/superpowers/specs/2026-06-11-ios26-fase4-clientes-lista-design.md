# iOS 26 — Fase 4: Clientes lista — Design

**Data:** 2026-06-11 (ciclo iOS 26)
**App:** `apps/tecnico-mobile`
**Tela:** `lib/features/clientes/clientes_list_screen.dart` (tela-raiz; Clientes foi dividido em fases — esta é só a LISTA; detalhe e cadastro vêm depois).

## Objetivo
iOS 26 na lista de clientes, mesmo padrão do Estoque: header de vidro + `CustomScrollView`, KPI rolando e busca+filtros FIXOS (pinned).

## Decisão do Robert
Filtros SGP (Todos / Sincronizado / Pendente SGP) **mantêm os chips com ícone/cor**
(☁ Sincronizado verde, ☁ Pendente âmbar) — NÃO viram segmented control —, só
reorganizados dentro da barra fixa.

## Mudanças
1. `AppBar` → **`IosGlassHeader('Clientes', actions: [refresh])`** (tela-raiz, sem voltar). Fundo segue `scheme.surface`.
2. Corpo → `RefreshIndicator`→`CustomScrollView(AlwaysScrollable, slivers:[...])`:
   - `IosGlassHeader`.
   - `SliverToBoxAdapter` com a **KPI "Pendentes de sincronização"** (mesmo `Builder` + `async.maybeWhen`, com o `onTap` que alterna o filtro 'pending') — **rola**.
   - `SliverPersistentHeader(pinned: true, delegate: _ClientesSearchHeader(...))` — **busca + chips FIXOS** sob o header.
   - `...async.when<List<Widget>>`: loading → `SliverFillRemaining(_StateBody loading)`; error → `SliverFillRemaining(_ErroView)`; data → vazio? `SliverFillRemaining(_VazioView)` : `SliverPadding(only(top:2,bottom:88), sliver: SliverList.builder(ClienteCard))`.
3. **`_ClientesSearchHeader`** (novo, privado, `SliverPersistentHeaderDelegate`, altura ~116, fundo `scheme.surface`): contém o `TextField` de busca (com `FocusNode` estável da State + clear) e a `Row` horizontal dos 3 `_FilterChip` atuais (Todos/Sincronizado/Pendente SGP) — mesmos widgets/cores/ícones de hoje, recebendo controller/focus/estado/callbacks. `shouldRebuild` compara `currentText`/`sgpFilter`/`background`.
4. `_FilterChip` (classe atual) **mantida** e reusada dentro do delegate.

## Não muda
- Lógica de busca/debounce (`_onBuscaChanged`), `_toggleSgp`, `clienteListFilterProvider`, `ClienteCard`, FAB "Novo" (no MainShell), dados/providers.

## Critérios de sucesso
1. Header de vidro "Clientes" + atualizar; KPI rola; **busca + chips ficam fixos** ao rolar.
2. Buscar/clear/chips/KPI-toggle funcionam igual; lista filtra igual; pull-to-refresh ok; teclado não cai ao digitar (FocusNode estável).
3. Fundo cinza, `ClienteCard` brancos destacando; vazio/erro ok.
4. `flutter analyze` limpo (deploy).
5. Visual on-device (claro/escuro): nada quebrado.

## Riscos
- Altura fixa ~116 do delegate (search + chip row): manter folga; ajustar on-device se cortar.
- `async.when<List<Widget>>` + spread: tipo explícito nos 3 branches.
- Sem teste automatizado (tela com provider sem harness; refactor visual) — validar via analyze + on-device, como na Fase 3.
- Duplicação leve do padrão de header pinned com o Estoque (`_SearchHeaderDelegate`) — aceitável; cleanup futuro pode extrair um `AppPinnedHeader` genérico.
