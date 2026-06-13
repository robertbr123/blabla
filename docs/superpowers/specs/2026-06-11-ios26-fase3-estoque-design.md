# iOS 26 — Fase 3: Estoque — Design

**Data:** 2026-06-11 (ciclo iOS 26)
**App:** `apps/tecnico-mobile`
**Tela:** `lib/features/estoque/estoque_screen.dart`

## Objetivo
Aplicar iOS 26 no Estoque: header de vidro + corpo em `CustomScrollView`, com a
**barra de busca fixa (pinned)** logo abaixo do header e os KPIs rolando.

## Mudanças

`EstoqueScreen` hoje: `Scaffold` + `AppBar` (só refresh) + `async.when` → `Column`
[KPIs · busca+filtro · `Expanded(RefreshIndicator(ListView de _ItemTile))`].

Passa a ser:
1. `AppBar` → **`IosGlassHeader(title: 'Estoque', actions: [refresh])`** — tela-raiz, **sem voltar** (`showBackButton` default false). Fundo segue `scheme.surface`.
2. Corpo vira `RefreshIndicator` → `CustomScrollView(physics: AlwaysScrollable, slivers:[...])`:
   - 1º sliver: `IosGlassHeader`.
   - `...async.when<List<Widget>>(...)`:
     - `loading` → `[SliverFillRemaining(hasScrollBody:false, child:_StateBody(AppStatePanel.loading))]`.
     - `error` → `[SliverFillRemaining(hasScrollBody:false, child:_Erro(...))]`.
     - `data(todas)` → calcula `filtradas`/`totalItens`/`categorias`/`hasZerosOcultos`/`hasActiveRefinement` (mesma lógica de hoje) e retorna a lista de slivers:
       - `SliverToBoxAdapter` com a **KPI strip** (3 `BrandKpiCard`, igual hoje) — **rola**.
       - `SliverPersistentHeader(pinned: true, delegate: _SearchHeaderDelegate(...))` — **busca + filtro FIXOS** sob o header.
       - itens: `SliverFillRemaining(_Vazio)` se vazio, senão `SliverList.builder` de `_ItemTile` (mesmo padding).
3. **`_SearchHeaderDelegate`** (novo, privado, `SliverPersistentHeaderDelegate`): altura fixa (~112), fundo `scheme.surface`, contém o `TextField` de busca (com clear) + a `Row` [chip "Mostrar zerados" + "Limpar" condicional] — exatamente os mesmos widgets/comportamento de hoje, recebendo controller + estado + callbacks da `State`. `min/maxExtent = 112`; `shouldRebuild` quando muda `mostrarZerados`/`hasActiveRefinement`/`background`.
4. **Filtro "Mostrar zerados" continua chip toggle** (booleano — não é segmented control).

## Não muda
- Lógica de busca/debounce (`_onSearchChanged`), filtro de zerados, KPIs, `_ItemTile`, `_Vazio`, `_Erro`, dados, providers.

## Critérios de sucesso
1. Header de vidro "Estoque" + atualizar; KPIs rolam; **busca fica fixa** abaixo do header ao rolar.
2. Busca/clear/chip/Limpar funcionam igual; lista filtra igual; pull-to-refresh funciona.
3. Fundo cinza agrupado, cards (`_ItemTile`) brancos destacando.
4. `flutter analyze` limpo + testes passando (deploy).
5. Visual on-device (claro/escuro): nada quebrado, busca gruda certinho.

## Riscos
- Altura fixa do `_SearchHeaderDelegate` (~112): se o `TextField`+row passar disso, dá overflow — manter folga e **ajustar on-device** se preciso (conteúdo ~98 < 112).
- `async.when<List<Widget>>` + spread (`...`): garantir o tipo de retorno explícito pros 3 branches.
- TextField dentro de header pinned que rebuilda: o controller é o da `State` (preserva texto/foco) — ok.
