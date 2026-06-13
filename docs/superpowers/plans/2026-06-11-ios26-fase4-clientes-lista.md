# iOS 26 Fase 4 (Clientes lista) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** iOS 26 na lista de clientes — header de vidro + `CustomScrollView`, busca+chips FIXOS (pinned), KPI rolando.

**Architecture:** `clientes_list_screen.dart`: `AppBar`+`Column/Expanded` → `RefreshIndicator`→`CustomScrollView` com `IosGlassHeader`, KPI sliver, `SliverPersistentHeader` pinned (busca + chips via novo `_ClientesSearchHeader`) e `SliverList` de `ClienteCard`. `FocusNode` estável na busca.

**Tech Stack:** Flutter (Material 3), `SliverPersistentHeader`, `SliverList`, `SliverFillRemaining`.

> **Ambiente:** sem Flutter local — analyze no deploy. Commit `--no-verify`. Stay on `main`. Sem teste automatizado (refactor visual; tela com provider sem harness).

---

## File Structure
- **Modify:** `lib/features/clientes/clientes_list_screen.dart` — import header, FocusNode na State, reescrita do `build`, novo `_ClientesSearchHeader`. `_FilterChip` mantido.

---

### Task 1: Clientes lista com header de vidro + busca/chips fixos

**Files:**
- Modify: `lib/features/clientes/clientes_list_screen.dart`

- [ ] **Step 1: Import + FocusNode na State**

(a) Adicionar import:
```dart
import '../../core/ui/ios_glass_header.dart';
```
(b) Na `_ClientesListScreenState`, adicionar o campo após `_busca`:
```dart
  final _buscaFocus = FocusNode();
```
e no `dispose()` (antes de `_busca.dispose()`):
```dart
    _buscaFocus.dispose();
```

- [ ] **Step 2: Reescrever o `return Scaffold(...)` do `build`**

Substituir TODO o `return Scaffold(...)` por:
```dart
    return Scaffold(
      backgroundColor: scheme.surface,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(clientesListProvider),
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            IosGlassHeader(
              title: 'Clientes',
              actions: [
                IconButton(
                  icon: const Icon(Icons.refresh),
                  tooltip: 'Atualizar',
                  onPressed: () => ref.invalidate(clientesListProvider),
                ),
              ],
            ),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                child: Builder(builder: (_) {
                  final visiveis = async.maybeWhen(
                      data: (page) => page.items.length, orElse: () => 0);
                  final pendentes = async.maybeWhen(
                      data: (page) =>
                          page.items.where((c) => c.sgpSyncedAt == null).length,
                      orElse: () => 0);
                  return BrandKpiCard(
                    label: 'Pendentes de sincronização',
                    value: '$pendentes',
                    icon: Icons.cloud_off_outlined,
                    tone: pendentes > 0 ? BrandTone.warning : BrandTone.success,
                    onTap: visiveis > 0
                        ? () {
                            _toggleSgp(
                                _sgpFilter == 'pending' ? null : 'pending');
                          }
                        : null,
                  );
                }),
              ),
            ),
            SliverPersistentHeader(
              pinned: true,
              delegate: _ClientesSearchHeader(
                controller: _busca,
                focusNode: _buscaFocus,
                currentText: _busca.text,
                sgpFilter: _sgpFilter,
                background: scheme.surface,
                onSearchChanged: _onBuscaChanged,
                onClearSearch: () {
                  _busca.clear();
                  _onBuscaChanged('');
                },
                onToggleSgp: _toggleSgp,
              ),
            ),
            ...async.when<List<Widget>>(
              loading: () => const [
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: _StateBody(
                    child: AppStatePanel.loading(
                      title: 'Carregando clientes',
                      message:
                          'Atualizando a base do dia para você buscar cidade, serial e status SGP sem ruído.',
                    ),
                  ),
                ),
              ],
              error: (e, _) => [
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: _ErroView(
                    e: e,
                    onRetry: () => ref.invalidate(clientesListProvider),
                  ),
                ),
              ],
              data: (page) {
                if (page.items.isEmpty) {
                  return [
                    SliverFillRemaining(
                      hasScrollBody: false,
                      child: _VazioView(
                        hasSearch:
                            _busca.text.isNotEmpty || _sgpFilter != null,
                      ),
                    ),
                  ];
                }
                return [
                  SliverPadding(
                    padding: const EdgeInsets.only(top: 2, bottom: 88),
                    sliver: SliverList.builder(
                      itemCount: page.items.length,
                      itemBuilder: (_, i) {
                        final c = page.items[i];
                        return ClienteCard(
                          item: c,
                          onTap: () => context.push('/clientes/${c.id}'),
                        );
                      },
                    ),
                  ),
                ];
              },
            ),
          ],
        ),
      ),
    );
```

- [ ] **Step 3: Adicionar `_ClientesSearchHeader` (antes de `_FilterChip`)**

```dart
/// Header pinned com a busca + filtros SGP (fica fixo sob o IosGlassHeader).
class _ClientesSearchHeader extends SliverPersistentHeaderDelegate {
  _ClientesSearchHeader({
    required this.controller,
    required this.focusNode,
    required this.currentText,
    required this.sgpFilter,
    required this.background,
    required this.onSearchChanged,
    required this.onClearSearch,
    required this.onToggleSgp,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final String currentText;
  final String? sgpFilter;
  final Color background;
  final ValueChanged<String> onSearchChanged;
  final VoidCallback onClearSearch;
  final ValueChanged<String?> onToggleSgp;

  static const _height = 116.0;

  @override
  double get minExtent => _height;

  @override
  double get maxExtent => _height;

  @override
  Widget build(
      BuildContext context, double shrinkOffset, bool overlapsContent) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      color: background,
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 8),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          TextField(
            controller: controller,
            focusNode: focusNode,
            onChanged: onSearchChanged,
            decoration: InputDecoration(
              prefixIcon: const Icon(Icons.search, size: 20),
              hintText: 'Buscar por nome, CPF, cidade, serial…',
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
          SizedBox(
            height: 36,
            child: ListView(
              scrollDirection: Axis.horizontal,
              children: [
                _FilterChip(
                  label: 'Todos',
                  selected: sgpFilter == null,
                  onTap: () => onToggleSgp(null),
                ),
                const SizedBox(width: 8),
                _FilterChip(
                  label: 'Sincronizado',
                  icon: Icons.cloud_done,
                  color: scheme.primary,
                  selected: sgpFilter == 'synced',
                  onTap: () => onToggleSgp('synced'),
                ),
                const SizedBox(width: 8),
                _FilterChip(
                  label: 'Pendente SGP',
                  icon: Icons.cloud_off,
                  color: const Color(0xFFF59E0B),
                  selected: sgpFilter == 'pending',
                  onTap: () => onToggleSgp('pending'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  bool shouldRebuild(covariant _ClientesSearchHeader oldDelegate) {
    return currentText != oldDelegate.currentText ||
        sgpFilter != oldDelegate.sgpFilter ||
        background != oldDelegate.background ||
        controller != oldDelegate.controller ||
        focusNode != oldDelegate.focusNode;
  }
}
```

- [ ] **Step 4: Analyze (deploy)**

Run: `flutter analyze lib/features/clientes/clientes_list_screen.dart`
Expected: `No issues found!` (rodar `dart format` no arquivo se acusar formatação).

- [ ] **Step 5: Commit**

```bash
git add lib/features/clientes/clientes_list_screen.dart
git commit --no-verify -m "feat(tecnico-mobile): Clientes lista com header de vidro + busca/chips fixos (iOS 26)"
```

---

### Task 2: Verificação

- [ ] **Step 1: Analyze (deploy)** — `flutter analyze lib/features/clientes/` → limpo.
- [ ] **Step 2: Visual on-device (claro/escuro):**
  - header de vidro "Clientes" + atualizar; KPI rola; **busca + chips ficam FIXOS** ao rolar;
  - buscar/clear/chips/KPI-toggle funcionam; lista filtra igual; pull-to-refresh ok; teclado não cai ao digitar;
  - fundo cinza, cards brancos; vazio/erro ok; toca num cliente → abre detalhe.

---

## Self-Review

**Spec coverage:**
- `IosGlassHeader('Clientes', refresh)` sem voltar → Step 2. ✅
- KPI sliver (rola, com onTap toggle) → Step 2. ✅
- Busca + chips fixos (`SliverPersistentHeader`/`_ClientesSearchHeader`) com ícone/cor mantidos → Steps 2-3. ✅
- `FocusNode` estável + `currentText` no shouldRebuild → Steps 1,3. ✅
- loading/erro/vazio em `SliverFillRemaining`; lista em `SliverPadding`→`SliverList` (bottom 88) → Step 2. ✅
- `_FilterChip` mantido → Step 3 reusa. ✅
- Lógica/dados intactos. ✅

**Placeholder scan:** sem TBD; código completo.

**Type consistency:** `_ClientesSearchHeader` campos batem com a chamada; `onSearchChanged: ValueChanged<String>` = `_onBuscaChanged(String)`; `onToggleSgp: ValueChanged<String?>` = `_toggleSgp(String?)`; `async.when<List<Widget>>` nos 3 branches.
