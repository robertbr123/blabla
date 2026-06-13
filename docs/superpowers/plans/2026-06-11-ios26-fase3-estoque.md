# iOS 26 Fase 3 (Estoque) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** iOS 26 no Estoque — header de vidro + `CustomScrollView` com busca FIXA (pinned) e KPIs rolando.

**Architecture:** `estoque_screen.dart`: `AppBar`+`Column/Expanded(ListView)` → `RefreshIndicator`→`CustomScrollView` com `IosGlassHeader`, KPI sliver, `SliverPersistentHeader` pinned (busca+filtro) e `SliverList` de itens. Novo `_SearchHeaderDelegate` privado.

**Tech Stack:** Flutter (Material 3), `SliverPersistentHeader`, `SliverList`, `SliverFillRemaining`.

> **Ambiente:** sem Flutter local — `flutter analyze`/test no deploy. Commitar com `git commit --no-verify`. Stay on `main`.
> **Sem teste automatizado nesta fase:** é refactor visual (lógica intacta) numa tela dependente de provider sem harness de teste hoje; validação via `flutter analyze` + on-device. Coerente com YAGNI aqui.

---

## File Structure
- **Modify:** `lib/features/estoque/estoque_screen.dart` — import do header, reescrita do `build`, novo `_SearchHeaderDelegate`.

---

### Task 1: Estoque com header de vidro + busca pinned

**Files:**
- Modify: `lib/features/estoque/estoque_screen.dart`

- [ ] **Step 1: Import do header**

Adicionar junto aos imports de `core/ui`:
```dart
import '../../core/ui/ios_glass_header.dart';
```

- [ ] **Step 2: Reescrever o `build` (estado data vira slivers)**

Substituir TODO o `return Scaffold(...)` do método `build` por:
```dart
    return Scaffold(
      backgroundColor: scheme.surface,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(estoqueSaldoProvider),
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            const IosGlassHeaderEstoqueActions(),
            ...async.when<List<Widget>>(
              loading: () => const [
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: _StateBody(
                    child: AppStatePanel.loading(
                      title: 'Carregando estoque',
                      message:
                          'Conferindo saldo e categorias para sua próxima visita.',
                    ),
                  ),
                ),
              ],
              error: (e, _) => [
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: _Erro(
                    e: e,
                    onRetry: () => ref.invalidate(estoqueSaldoProvider),
                  ),
                ),
              ],
              data: (todas) {
                final filtradas = todas.where((l) {
                  if (!_mostrarZerados && l.saldo <= 0) return false;
                  if (query.isEmpty) return true;
                  return l.nome.toLowerCase().contains(query) ||
                      l.sku.toLowerCase().contains(query) ||
                      l.categoria.toLowerCase().contains(query);
                }).toList();

                final totalItens = todas.fold<int>(
                    0, (a, l) => a + (l.saldo > 0 ? l.saldo : 0));
                final categorias =
                    <String>{for (final l in todas) l.categoria}.length;
                final hasZerosOcultos =
                    !_mostrarZerados && todas.any((l) => l.saldo <= 0);
                final hasActiveRefinement =
                    query.isNotEmpty || _mostrarZerados;

                return [
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                      child: Row(
                        children: [
                          Expanded(
                            child: BrandKpiCard(
                              label: 'Itens',
                              value: '$totalItens',
                              icon: Icons.inventory_2_outlined,
                              tone: BrandTone.info,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: BrandKpiCard(
                              label: 'Categorias',
                              value: '$categorias',
                              icon: Icons.category_outlined,
                              tone: BrandTone.warning,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: BrandKpiCard(
                              label: 'Visíveis',
                              value: '${filtradas.length}',
                              icon: Icons.visibility_outlined,
                              tone: BrandTone.success,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  SliverPersistentHeader(
                    pinned: true,
                    delegate: _SearchHeaderDelegate(
                      controller: _searchCtrl,
                      mostrarZerados: _mostrarZerados,
                      hasActiveRefinement: hasActiveRefinement,
                      background: scheme.surface,
                      onSearchChanged: _onSearchChanged,
                      onClearSearch: () {
                        _searchCtrl.clear();
                        setState(() {});
                      },
                      onToggleZerados: (v) =>
                          setState(() => _mostrarZerados = v),
                      onClearAll: () {
                        _searchCtrl.clear();
                        setState(() => _mostrarZerados = false);
                      },
                    ),
                  ),
                  if (filtradas.isEmpty)
                    SliverFillRemaining(
                      hasScrollBody: false,
                      child: _Vazio(
                        hasActiveRefinement: hasActiveRefinement,
                        hasZerosOcultos: hasZerosOcultos,
                      ),
                    )
                  else
                    SliverList.builder(
                      itemCount: filtradas.length,
                      itemBuilder: (_, i) => Padding(
                        padding: EdgeInsets.fromLTRB(16, i == 0 ? 2 : 0, 16, 12),
                        child: _ItemTile(linha: filtradas[i]),
                      ),
                    ),
                  const SliverToBoxAdapter(child: SizedBox(height: 24)),
                ];
              },
            ),
          ],
        ),
      ),
    );
```
NOTA: o `const IosGlassHeaderEstoqueActions()` acima é um placeholder textual — **não** crie esse widget. Em vez disso, use o `IosGlassHeader` real assim (substitua aquela linha por):
```dart
            IosGlassHeader(
              title: 'Estoque',
              actions: [
                IconButton(
                  icon: const Icon(Icons.refresh),
                  tooltip: 'Atualizar',
                  onPressed: () => ref.invalidate(estoqueSaldoProvider),
                ),
              ],
            ),
```

- [ ] **Step 3: Adicionar o `_SearchHeaderDelegate`**

No fim do arquivo (depois de `_StateBody`), adicionar:
```dart
/// Header pinned com a busca + filtro do estoque (fica fixo sob o IosGlassHeader).
class _SearchHeaderDelegate extends SliverPersistentHeaderDelegate {
  _SearchHeaderDelegate({
    required this.controller,
    required this.mostrarZerados,
    required this.hasActiveRefinement,
    required this.background,
    required this.onSearchChanged,
    required this.onClearSearch,
    required this.onToggleZerados,
    required this.onClearAll,
  });

  final TextEditingController controller;
  final bool mostrarZerados;
  final bool hasActiveRefinement;
  final Color background;
  final VoidCallback onSearchChanged;
  final VoidCallback onClearSearch;
  final ValueChanged<bool> onToggleZerados;
  final VoidCallback onClearAll;

  static const _height = 112.0;

  @override
  double get minExtent => _height;

  @override
  double get maxExtent => _height;

  @override
  Widget build(
      BuildContext context, double shrinkOffset, bool overlapsContent) {
    return Container(
      color: background,
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 8),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          TextField(
            controller: controller,
            onChanged: (_) => onSearchChanged(),
            decoration: InputDecoration(
              prefixIcon: const Icon(Icons.search, size: 20),
              hintText: 'Buscar por nome, SKU ou categoria',
              isDense: true,
              suffixIcon: controller.text.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.clear, size: 18),
                      onPressed: onClearSearch,
                    )
                  : null,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              FilterChip(
                label: const Text('Mostrar zerados'),
                selected: mostrarZerados,
                onSelected: onToggleZerados,
                visualDensity: VisualDensity.compact,
              ),
              const Spacer(),
              if (hasActiveRefinement)
                TextButton.icon(
                  onPressed: onClearAll,
                  icon: const Icon(Icons.clear_all, size: 16),
                  label: const Text('Limpar'),
                  style: TextButton.styleFrom(
                    visualDensity: VisualDensity.compact,
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  @override
  bool shouldRebuild(covariant _SearchHeaderDelegate oldDelegate) {
    return mostrarZerados != oldDelegate.mostrarZerados ||
        hasActiveRefinement != oldDelegate.hasActiveRefinement ||
        background != oldDelegate.background ||
        controller != oldDelegate.controller;
  }
}
```

- [ ] **Step 4: Conferir imports não usados**

Após a reescrita, o `Column`/`Expanded` antigos somem. Conferir que `BrandKpiCard`, `BrandTone`, `AppStatePanel`, `AppSurfaceCard` (usado em `_ItemTile`), `estoque_data` seguem importados e usados. Remover só o que ficou órfão (provavelmente nada — todos seguem em uso).

- [ ] **Step 5: Analyze (deploy)**

Run: `flutter analyze lib/features/estoque/estoque_screen.dart`
Expected: `No issues found!`. (Se acusar `dart format`, rodar `dart format` no arquivo.)

- [ ] **Step 6: Commit**

```bash
git add lib/features/estoque/estoque_screen.dart
git commit --no-verify -m "feat(tecnico-mobile): Estoque com header de vidro + busca fixa (iOS 26)"
```

---

### Task 2: Verificação

- [ ] **Step 1: Analyze (deploy)** — `flutter analyze lib/features/estoque/` → limpo.
- [ ] **Step 2: Visual on-device (claro/escuro):**
  - header de vidro "Estoque" + atualizar; KPIs rolam; **busca + filtro ficam FIXOS** sob o header ao rolar a lista;
  - buscar/clear/"Mostrar zerados"/"Limpar" funcionam; lista filtra igual; pull-to-refresh ok;
  - fundo cinza, cards brancos; estado vazio e erro ok;
  - **conferir a altura do `_SearchHeaderDelegate`** (112) — se cortar/sobrar muito, ajustar.

---

## Self-Review

**Spec coverage:**
- `IosGlassHeader('Estoque', refresh)`, sem voltar → Step 2. ✅
- `CustomScrollView` + `RefreshIndicator` externo + `AlwaysScrollable` → Step 2. ✅
- KPI sliver (rola) + busca pinned (`SliverPersistentHeader`) + `SliverList`/`_Vazio` → Step 2. ✅
- `_SearchHeaderDelegate` com mesmos widgets/comportamento → Step 3. ✅
- loading/erro em `SliverFillRemaining` → Step 2. ✅
- Chip toggle mantido (não vira segmented) → Step 3. ✅
- Lógica/dados intactos → só reorganização visual. ✅

**Placeholder scan:** o único "placeholder" é o `IosGlassHeaderEstoqueActions` explicitamente marcado no Step 2 com a substituição real logo abaixo — implementador usa o bloco `IosGlassHeader(...)`. Sem TBD reais.

**Type consistency:** `async.when<List<Widget>>` nos 3 branches retorna `List<Widget>`; `_SearchHeaderDelegate` campos batem com a chamada; `_ItemTile`/`_Vazio`/`_Erro`/`_StateBody` inalterados.
