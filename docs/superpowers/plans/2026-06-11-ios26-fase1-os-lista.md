# iOS 26 Fase 1 (OS lista + componentes) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aplicar iOS 26 na OS lista criando os componentes reutilizáveis `IosGlassHeader` (large-title de vidro) e `AppSegmentedControl<T>` (segmentado iOS).

**Architecture:** Dois widgets novos em `lib/core/ui/`, consumidos pela `os_list_screen.dart`. O header vira o primeiro sliver do `CustomScrollView` existente; o segmented control substitui o `HomeFilterStrip`. Nenhuma lógica de dados/filtro/sync muda.

**Tech Stack:** Flutter (Material 3), `dart:ui` `ImageFilter.blur`, `SliverAppBar.large`/`FlexibleSpaceBar`.

> **Nota de ambiente:** sem Flutter local — `flutter test`/`analyze` rodam no deploy/CI. Commitar SEMPRE com `git commit --no-verify`. Stay on `main`.

---

## File Structure
- **Create:** `lib/core/ui/app_segmented_control.dart` — `AppSegmentedControl<T>` + `AppSegment<T>`.
- **Create:** `lib/core/ui/ios_glass_header.dart` — `IosGlassHeader` (StatelessWidget → SliverAppBar).
- **Create:** `test/core/ui/app_segmented_control_test.dart`, `test/core/ui/ios_glass_header_test.dart`.
- **Modify:** `lib/features/os/os_list_screen.dart`.

---

### Task 1: `AppSegmentedControl<T>`

**Files:**
- Create: `lib/core/ui/app_segmented_control.dart`
- Test: `test/core/ui/app_segmented_control_test.dart`

- [ ] **Step 1: Teste**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/branding/brand_theme.dart';
import 'package:tecnico_mobile/core/ui/app_segmented_control.dart';

void main() {
  const segs = [
    AppSegment(value: 0, label: 'Todas'),
    AppSegment(value: 1, label: 'Em andamento'),
    AppSegment(value: 2, label: 'Concluídas'),
  ];

  testWidgets('renderiza labels e dispara onChanged ao tocar', (tester) async {
    int? picked;
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBrandTheme(Brightness.light),
        home: Scaffold(
          body: AppSegmentedControl<int>(
            segments: segs,
            selected: 0,
            onChanged: (v) => picked = v,
          ),
        ),
      ),
    );
    for (final s in segs) {
      expect(find.text(s.label), findsOneWidget);
    }
    await tester.tap(find.text('Concluídas'));
    await tester.pump();
    expect(picked, 2);
  });

  testWidgets('tocar no já selecionado não dispara onChanged', (tester) async {
    var calls = 0;
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBrandTheme(Brightness.light),
        home: Scaffold(
          body: AppSegmentedControl<int>(
            segments: segs,
            selected: 0,
            onChanged: (_) => calls++,
          ),
        ),
      ),
    );
    await tester.tap(find.text('Todas'));
    await tester.pump();
    expect(calls, 0);
  });
}
```

- [ ] **Step 2: Rodar e ver falhar (deploy)**

Run: `flutter test test/core/ui/app_segmented_control_test.dart`
Expected: FALHA de compilação (`AppSegmentedControl`/`AppSegment` não existem).

- [ ] **Step 3: Implementar**

Criar `lib/core/ui/app_segmented_control.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Um segmento do [AppSegmentedControl].
class AppSegment<T> {
  final T value;
  final String label;
  const AppSegment({required this.value, required this.label});
}

/// Seletor segmentado estilo iOS — track arredondado com pílula no item ativo.
/// Rola na horizontal quando os segmentos não cabem (labels longos não truncam).
class AppSegmentedControl<T> extends StatelessWidget {
  const AppSegmentedControl({
    super.key,
    required this.segments,
    required this.selected,
    required this.onChanged,
  });

  final List<AppSegment<T>> segments;
  final T selected;
  final ValueChanged<T> onChanged;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: scheme.surfaceContainerHigh,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Padding(
          padding: const EdgeInsets.all(3),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (final seg in segments)
                _Segment(
                  label: seg.label,
                  selected: seg.value == selected,
                  onTap: () {
                    if (seg.value == selected) return;
                    HapticFeedback.selectionClick();
                    onChanged(seg.value);
                  },
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Segment extends StatelessWidget {
  const _Segment({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final pillColor = isDark ? scheme.surfaceContainerHighest : Colors.white;

    return Semantics(
      button: true,
      selected: selected,
      label: label,
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOut,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: selected ? pillColor : Colors.transparent,
            borderRadius: BorderRadius.circular(9),
            boxShadow: selected
                ? [
                    BoxShadow(
                      color: scheme.shadow.withValues(alpha: 0.12),
                      blurRadius: 6,
                      offset: const Offset(0, 1),
                    ),
                  ]
                : null,
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: selected ? scheme.primary : scheme.onSurfaceVariant,
            ),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: Rodar testes (deploy)** — `flutter test test/core/ui/app_segmented_control_test.dart` → PASS.
- [ ] **Step 5: Commit**

```bash
git add lib/core/ui/app_segmented_control.dart test/core/ui/app_segmented_control_test.dart
git commit --no-verify -m "feat(tecnico-mobile): AppSegmentedControl iOS (track + pílula, rolável)"
```

---

### Task 2: `IosGlassHeader`

**Files:**
- Create: `lib/core/ui/ios_glass_header.dart`
- Test: `test/core/ui/ios_glass_header_test.dart`

- [ ] **Step 1: Teste**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/branding/brand_theme.dart';
import 'package:tecnico_mobile/core/ui/ios_glass_header.dart';

void main() {
  testWidgets('mostra título, ação e tem vidro (BackdropFilter)',
      (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBrandTheme(Brightness.light),
        home: Scaffold(
          body: CustomScrollView(
            slivers: [
              IosGlassHeader(
                title: 'Ordens de Serviço',
                subtitle: '3 ordens em foco',
                actions: [
                  IconButton(
                    icon: const Icon(Icons.refresh),
                    onPressed: () {},
                  ),
                ],
              ),
              const SliverToBoxAdapter(child: SizedBox(height: 1200)),
            ],
          ),
        ),
      ),
    );
    expect(find.text('Ordens de Serviço'), findsOneWidget);
    expect(find.byIcon(Icons.refresh), findsOneWidget);
    expect(find.byType(BackdropFilter), findsOneWidget);
  });
}
```

- [ ] **Step 2: Rodar e ver falhar (deploy)** — `IosGlassHeader` não existe.

- [ ] **Step 3: Implementar**

Criar `lib/core/ui/ios_glass_header.dart`:
```dart
import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

import '../branding/brand_theme.dart';

/// Header large-title de vidro estilo iOS 26.
/// Use como PRIMEIRO sliver de um CustomScrollView. O título grande colapsa
/// pro inline ao rolar e o fundo translúcido desfoca o conteúdo por baixo.
class IosGlassHeader extends StatelessWidget {
  const IosGlassHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.actions = const [],
  });

  final String title;
  final String? subtitle;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return SliverAppBar(
      pinned: true,
      expandedHeight: subtitle == null ? 104 : 120,
      backgroundColor: scheme.surface.withValues(alpha: 0.7),
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      automaticallyImplyLeading: false,
      actions: actions,
      flexibleSpace: ClipRect(
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
          child: FlexibleSpaceBar(
            expandedTitleScale: 1.0,
            titlePadding: const EdgeInsetsDirectional.only(
              start: 16,
              bottom: 12,
              end: 72,
            ),
            title: Column(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.end,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: iosLargeTitle(scheme)),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    subtitle!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 12.5,
                      color: scheme.onSurfaceVariant,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: Rodar testes (deploy)** → PASS.
- [ ] **Step 5: Commit**

```bash
git add lib/core/ui/ios_glass_header.dart test/core/ui/ios_glass_header_test.dart
git commit --no-verify -m "feat(tecnico-mobile): IosGlassHeader (large-title de vidro reutilizável)"
```

---

### Task 3: Adotar na OS lista (`os_list_screen.dart`)

**Files:**
- Modify: `lib/features/os/os_list_screen.dart`

- [ ] **Step 1: Imports**

Adicionar:
```dart
import '../../core/ui/app_segmented_control.dart';
import '../../core/ui/ios_glass_header.dart';
```
Remover o import agora não usado de `home_filter_strip.dart` SOMENTE se `HomeFilterStrip` deixar de ser referenciado (ver Step 3). Manter o import de `OsHomeFilter`/`OsHomeFilterX` — eles vêm de `home_filter_strip.dart` também, então **manter o import** `import 'widgets/home_filter_strip.dart';` (o enum/extension vivem lá).

- [ ] **Step 2: Remover o `appBar` e injetar o header como primeiro sliver**

No `Scaffold`, remover todo o parâmetro `appBar: AppBar(... )`. No estado `data`, dentro do `CustomScrollView`, inserir como PRIMEIRO sliver (antes do banner offline):
```dart
              slivers: [
                IosGlassHeader(
                  title: 'Ordens de Serviço',
                  subtitle: '${items.length} '
                      '${items.length == 1 ? 'ordem' : 'ordens'} em foco',
                  actions: [
                    IconButton(
                      icon: const Icon(Icons.refresh),
                      tooltip: 'Atualizar',
                      onPressed: () => ref.invalidate(osListStreamProvider),
                    ),
                    IconButton(
                      icon: const Icon(Icons.logout),
                      tooltip: 'Sair',
                      onPressed: _logout,
                    ),
                  ],
                ),
                if (pendingSync case AsyncData(:final value) when value > 0)
                  // ...resto dos slivers existentes inalterado...
```
(O `loading`/`error` continuam usando `_StateBody`/`_Erro` sem header — inalterados.)

- [ ] **Step 3: Trocar `HomeFilterStrip` pelo `AppSegmentedControl`**

Substituir o `SliverToBoxAdapter` do filtro:
```dart
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                    child: HomeFilterStrip(
                      filters: _filters,
                      selected: _selectedFilter,
                      onSelected: _selectFilter,
                    ),
                  ),
                ),
```
por:
```dart
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                    child: AppSegmentedControl<OsHomeFilter>(
                      segments: [
                        for (final f in _filters)
                          AppSegment(value: f, label: f.label),
                      ],
                      selected: _selectedFilter,
                      onChanged: _selectFilter,
                    ),
                  ),
                ),
```
(`_filters` e `_selectFilter` já existem; `OsHomeFilterX.label` já existe.)

- [ ] **Step 4: Conferir imports**

`HomeFilterStrip` não é mais usado, mas o arquivo `home_filter_strip.dart` ainda exporta `OsHomeFilter`/`OsHomeFilterX` que a tela usa — **manter** `import 'widgets/home_filter_strip.dart';`. Garantir que não sobrou referência a `HomeFilterStrip` na tela.

- [ ] **Step 5: Rodar testes + analyze (deploy)**

Run: `flutter test test/ && flutter analyze lib/features/os/os_list_screen.dart`
Expected: PASS / `No issues found!`.

- [ ] **Step 6: Commit**

```bash
git add lib/features/os/os_list_screen.dart
git commit --no-verify -m "feat(tecnico-mobile): OS lista com header de vidro + segmented control (iOS 26)"
```

---

### Task 4: Verificação

- [ ] **Step 1: Analyze (deploy)** — `flutter analyze lib/core/ui/ lib/features/os/os_list_screen.dart` → limpo.
- [ ] **Step 2: Visual on-device (claro/escuro):**
  - large title "Ordens de Serviço" aparece grande, colapsa ao rolar, com blur do conteúdo por baixo;
  - subtítulo com a contagem; ações refresh/sair funcionando;
  - segmented control legível, rola se precisar, troca de filtro com haptic e funciona igual;
  - KPI cards e lista inalterados; nada cortado.
  - **Anotar ajustes finos do header** (paddings/scale do large title) pra calibrar — ver risco abaixo.

---

## Self-Review

**Spec coverage:**
- `IosGlassHeader` reutilizável (SliverAppBar + BackdropFilter, title+subtitle+actions) → Task 2. ✅
- `AppSegmentedControl<T>` rolável com pílula → Task 1. ✅
- OS lista: header "Ordens de Serviço" + subtítulo dinâmico + ações → Task 3 Step 2. ✅
- KPIs/lista/sort/sync/logout inalterados → Task 3 só mexe no appBar e no sliver de filtro. ✅
- Filtros trocados pelo segmented mantendo os 5 estados → Task 3 Step 3. ✅

**Placeholder scan:** sem TBD; código completo em cada passo. ✅

**Type consistency:** `AppSegment<T>`/`AppSegmentedControl<T>` usados com `OsHomeFilter`; `_selectFilter` é `ValueChanged<OsHomeFilter>` (assinatura bate com `onChanged`); `iosLargeTitle(scheme)` da Fase 0 reutilizado. ✅

**Desvio consciente do spec:** o spec falava em "pílula deslizante"; com segmentos de largura variável + scroll, a pílula é renderizada por-segmento com `AnimatedContainer` (background animado) em vez de uma pílula física que desliza entre posições — mesmo efeito visual, muito mais robusto com larguras variáveis.

**Risco (já no spec):** o collapse do large title (`FlexibleSpaceBar` + Column título/subtítulo + `expandedTitleScale: 1.0`) pode precisar de ajuste fino de `titlePadding`/`expandedHeight` no aparelho — não dá pra prever sem rodar. Por isso a Fase 1 deve ser validada on-device antes de varrer as outras telas.
