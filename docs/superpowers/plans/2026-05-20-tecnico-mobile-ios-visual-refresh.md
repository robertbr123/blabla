# Técnico Mobile iPhone Visual Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformar o `tecnico-mobile` em uma experiência visual premium para iPhone, com home operacional centrada em OS e sistema visual consistente em `OS`, `Clientes`, `Estoque` e `Perfil`.

**Architecture:** A implementação começa pela fundação visual compartilhada no tema e em componentes reutilizáveis, depois reorganiza a aba principal em uma home `Hybrid iPhone` com lista de OS dominante. Em seguida, propaga a linguagem visual para detalhe de OS, clientes, estoque, perfil e estados de loading/erro/offline sem mudar regras de negócio.

**Tech Stack:** Flutter, Material 3, Riverpod, go_router, flutter_test

---

### Task 1: Criar fundação visual compartilhada

**Files:**
- Modify: `apps/tecnico-mobile/lib/core/theme.dart`
- Create: `apps/tecnico-mobile/lib/core/ui/app_surfaces.dart`
- Create: `apps/tecnico-mobile/lib/core/ui/app_section_header.dart`
- Create: `apps/tecnico-mobile/lib/core/ui/app_status_chip.dart`
- Test: `apps/tecnico-mobile/test/core/ui/app_visual_system_test.dart`

- [ ] **Step 1: Write the failing tests for the shared visual system**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/theme.dart';
import 'package:tecnico_mobile/core/ui/app_status_chip.dart';
import 'package:tecnico_mobile/core/ui/app_surfaces.dart';

void main() {
  testWidgets('premium theme exposes command-center palette', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildLightTheme(),
        home: const Scaffold(body: SizedBox()),
      ),
    );

    final context = tester.element(find.byType(SizedBox));
    final scheme = Theme.of(context).colorScheme;

    expect(scheme.primary.value, const Color(0xFF17324D).value);
    expect(scheme.surfaceContainerLowest.value, const Color(0xFFF6F1E8).value);
  });

  testWidgets('status chip renders label and accent', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildLightTheme(),
        home: const Scaffold(
          body: AppStatusChip(label: 'Em andamento', tone: AppStatusTone.info),
        ),
      ),
    );

    expect(find.text('Em andamento'), findsOneWidget);
  });

  testWidgets('surface card keeps rounded premium container', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildLightTheme(),
        home: const Scaffold(
          body: AppSurfaceCard(child: Text('Conteúdo')),
        ),
      ),
    );

    expect(find.text('Conteúdo'), findsOneWidget);
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/core/ui/app_visual_system_test.dart`
Expected: FAIL because the visual system widgets and palette do not exist yet

- [ ] **Step 3: Implement the premium palette and shared UI primitives**

```dart
// apps/tecnico-mobile/lib/core/ui/app_status_chip.dart
import 'package:flutter/material.dart';

enum AppStatusTone { neutral, info, success, warning, danger }

class AppStatusChip extends StatelessWidget {
  final String label;
  final AppStatusTone tone;
  const AppStatusChip({
    super.key,
    required this.label,
    this.tone = AppStatusTone.neutral,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final color = switch (tone) {
      AppStatusTone.info => scheme.primary,
      AppStatusTone.success => const Color(0xFF2E7D5B),
      AppStatusTone.warning => const Color(0xFFC18A2D),
      AppStatusTone.danger => scheme.error,
      AppStatusTone.neutral => scheme.onSurfaceVariant,
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.18)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w700,
          color: color,
          letterSpacing: 0.1,
        ),
      ),
    );
  }
}
```

```dart
// apps/tecnico-mobile/lib/core/ui/app_surfaces.dart
import 'package:flutter/material.dart';

class AppSurfaceCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  const AppSurfaceCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: scheme.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: scheme.outlineVariant.withValues(alpha: 0.55)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 26,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: child,
    );
  }
}
```

```dart
// apps/tecnico-mobile/lib/core/theme.dart
const brandCommand = Color(0xFF17324D);
const brandAccent = Color(0xFFC18A2D);
const brandWarm = Color(0xFFF6F1E8);
const brandSurface = Color(0xFFFFFCF8);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/core/ui/app_visual_system_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/core/theme.dart apps/tecnico-mobile/lib/core/ui/app_surfaces.dart apps/tecnico-mobile/lib/core/ui/app_section_header.dart apps/tecnico-mobile/lib/core/ui/app_status_chip.dart apps/tecnico-mobile/test/core/ui/app_visual_system_test.dart
git commit -m "feat: add tecnico mobile premium visual system"
```

### Task 2: Transformar a primeira aba em Home operacional

**Files:**
- Modify: `apps/tecnico-mobile/lib/features/shell/main_shell.dart`
- Modify: `apps/tecnico-mobile/lib/features/os/os_list_screen.dart`
- Create: `apps/tecnico-mobile/lib/features/os/widgets/home_hero.dart`
- Create: `apps/tecnico-mobile/lib/features/os/widgets/home_filter_strip.dart`
- Create: `apps/tecnico-mobile/lib/features/os/widgets/home_summary_card.dart`
- Test: `apps/tecnico-mobile/test/features/os/os_home_screen_test.dart`

- [ ] **Step 1: Write the failing home-focused tests**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:tecnico_mobile/features/os/os_list_screen.dart';

void main() {
  testWidgets('home screen shows operational hero and os list', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(home: OsListScreen()),
      ),
    );

    expect(find.textContaining('Hoje'), findsOneWidget);
    expect(find.textContaining('Pendentes'), findsWidgets);
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/features/os/os_home_screen_test.dart`
Expected: FAIL because the current screen only exposes the old list shell

- [ ] **Step 3: Rework the screen into a hybrid iPhone home**

```dart
// apps/tecnico-mobile/lib/features/shell/main_shell.dart
static const _telas = [
  OsListScreen(),
  EstoqueScreen(),
  ClientesListScreen(),
  PerfilScreen(),
];

static const _rotas = ['/os', '/estoque', '/clientes', '/perfil'];

// first destination becomes Home visually while preserving route compatibility
NavigationDestination(
  icon: Icon(Icons.home_outlined),
  selectedIcon: Icon(Icons.home_rounded),
  label: 'Home',
),
```

```dart
// apps/tecnico-mobile/lib/features/os/os_list_screen.dart
return Scaffold(
  backgroundColor: scheme.surfaceContainerLowest,
  appBar: AppBar(
    title: const Text('Home'),
    actions: [...],
  ),
  body: async.when(
    data: (rows) {
      final items = rows.map(_OsItem.fromJson).toList()..sort(...);
      final filtered = _filterForSelectedTab(items);

      return RefreshIndicator(
        onRefresh: () async => ref.invalidate(osListStreamProvider),
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
          children: [
            HomeHero(
              total: items.length,
              pendentes: counts['pendente'] ?? 0,
              andamento: counts['em_andamento'] ?? 0,
            ),
            const SizedBox(height: 16),
            HomeFilterStrip(...),
            const SizedBox(height: 16),
            ...filtered.map((it) => OsCard(...)),
          ],
        ),
      );
    },
  ),
);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/features/os/os_home_screen_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/features/shell/main_shell.dart apps/tecnico-mobile/lib/features/os/os_list_screen.dart apps/tecnico-mobile/lib/features/os/widgets/home_hero.dart apps/tecnico-mobile/lib/features/os/widgets/home_filter_strip.dart apps/tecnico-mobile/lib/features/os/widgets/home_summary_card.dart apps/tecnico-mobile/test/features/os/os_home_screen_test.dart
git commit -m "feat: turn os tab into premium operational home"
```

### Task 3: Refinar cards e detalhe de OS

**Files:**
- Modify: `apps/tecnico-mobile/lib/features/os/widgets/os_card.dart`
- Modify: `apps/tecnico-mobile/lib/features/os/os_detail_screen.dart`
- Modify: `apps/tecnico-mobile/lib/features/os/widgets/cliente_avatar.dart`
- Test: `apps/tecnico-mobile/test/features/os/os_detail_screen_test.dart`

- [ ] **Step 1: Extend the OS detail tests with premium sections**

```dart
testWidgets('os detail groups actions and context in separate sections', (tester) async {
  await pumpOsDetail(tester);

  expect(find.textContaining('Status'), findsOneWidget);
  expect(find.textContaining('Fotos'), findsOneWidget);
  expect(find.textContaining('Ações'), findsOneWidget);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/features/os/os_detail_screen_test.dart`
Expected: FAIL because the new grouped sections are not present yet

- [ ] **Step 3: Apply the new OS visual hierarchy**

```dart
// apps/tecnico-mobile/lib/features/os/widgets/os_card.dart
return Padding(
  padding: const EdgeInsets.only(bottom: 12),
  child: AppSurfaceCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: Text(nomeCliente ?? codigo, style: titleStyle)),
            AppStatusChip(label: statusLabel, tone: tone),
          ],
        ),
        const SizedBox(height: 10),
        Text(endereco, style: subtitleStyle),
        const SizedBox(height: 14),
        Row(
          children: [
            _MetaPill(icon: Icons.bolt, label: problema),
            const Spacer(),
            Icon(Icons.chevron_right_rounded),
          ],
        ),
      ],
    ),
  ),
);
```

```dart
// apps/tecnico-mobile/lib/features/os/os_detail_screen.dart
ListView(
  padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
  children: [
    AppSurfaceCard(child: _StatusHeader(...)),
    const SizedBox(height: 12),
    AppSurfaceCard(child: _ContextSection(...)),
    const SizedBox(height: 12),
    AppSurfaceCard(child: _ActionsSection(...)),
    const SizedBox(height: 12),
    AppSurfaceCard(child: _PhotosSection(...)),
  ],
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/features/os/os_detail_screen_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/features/os/widgets/os_card.dart apps/tecnico-mobile/lib/features/os/os_detail_screen.dart apps/tecnico-mobile/lib/features/os/widgets/cliente_avatar.dart apps/tecnico-mobile/test/features/os/os_detail_screen_test.dart
git commit -m "feat: refine os cards and detail visual hierarchy"
```

### Task 4: Propagar o sistema visual para Clientes

**Files:**
- Modify: `apps/tecnico-mobile/lib/features/clientes/clientes_list_screen.dart`
- Modify: `apps/tecnico-mobile/lib/features/clientes/widgets/cliente_card.dart`
- Modify: `apps/tecnico-mobile/lib/features/clientes/cliente_detail_screen.dart`
- Modify: `apps/tecnico-mobile/lib/features/clientes/cliente_novo_screen.dart`
- Test: `apps/tecnico-mobile/test/features/clientes/cliente_visual_test.dart`

- [ ] **Step 1: Write the failing client visual tests**

```dart
testWidgets('clientes list shows premium search and section header', (tester) async {
  await pumpClientesList(tester);

  expect(find.textContaining('Clientes'), findsOneWidget);
  expect(find.byIcon(Icons.search), findsOneWidget);
});

testWidgets('novo cliente shows elevated step container', (tester) async {
  await pumpNovoCliente(tester);

  expect(find.textContaining('Novo cliente'), findsOneWidget);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/features/clientes/cliente_visual_test.dart`
Expected: FAIL because the helper screen expectations do not exist yet

- [ ] **Step 3: Rework list, detail and form surfaces**

```dart
// clientes_list_screen.dart
body: Column(
  children: [
    Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 10),
      child: AppSurfaceCard(
        child: Column(
          children: [
            TextField(...),
            const SizedBox(height: 10),
            _PremiumClientFilterRow(...),
          ],
        ),
      ),
    ),
    Expanded(...),
  ],
)
```

```dart
// cliente_detail_screen.dart
ListView(
  padding: const EdgeInsets.all(16),
  children: [
    AppSurfaceCard(child: _ClienteHero(...)),
    const SizedBox(height: 12),
    AppSurfaceCard(child: _DadosGerais(...)),
    const SizedBox(height: 12),
    ClienteFotosSection(...),
  ],
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/features/clientes/cliente_visual_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/features/clientes/clientes_list_screen.dart apps/tecnico-mobile/lib/features/clientes/widgets/cliente_card.dart apps/tecnico-mobile/lib/features/clientes/cliente_detail_screen.dart apps/tecnico-mobile/lib/features/clientes/cliente_novo_screen.dart apps/tecnico-mobile/test/features/clientes/cliente_visual_test.dart
git commit -m "feat: apply premium visual system to clientes flows"
```

### Task 5: Refinar Estoque e Perfil

**Files:**
- Modify: `apps/tecnico-mobile/lib/features/estoque/estoque_screen.dart`
- Modify: `apps/tecnico-mobile/lib/features/perfil/perfil_screen.dart`
- Modify: `apps/tecnico-mobile/lib/features/perfil/perfil_data.dart`
- Test: `apps/tecnico-mobile/test/features/estoque/estoque_screen_test.dart`
- Test: `apps/tecnico-mobile/test/features/perfil/perfil_screen_test.dart`

- [ ] **Step 1: Write the failing tests for refined sections**

```dart
testWidgets('estoque shows summary surface and premium filters', (tester) async {
  await pumpEstoque(tester);

  expect(find.textContaining('Itens em estoque'), findsOneWidget);
  expect(find.textContaining('Categorias'), findsOneWidget);
});

testWidgets('perfil groups account actions in premium sections', (tester) async {
  await pumpPerfil(tester);

  expect(find.text('Conta'), findsOneWidget);
  expect(find.text('Sobre'), findsOneWidget);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/features/estoque/estoque_screen_test.dart test/features/perfil/perfil_screen_test.dart`
Expected: FAIL because the tests and premium grouping are not present yet

- [ ] **Step 3: Update both screens to the shared visual language**

```dart
// estoque_screen.dart
Container(
  padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
  child: AppSurfaceCard(
    child: Column(
      children: [
        _ResumoPremium(...),
        const SizedBox(height: 12),
        TextField(...),
      ],
    ),
  ),
)
```

```dart
// perfil_screen.dart
ListView(
  padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
  children: [
    AppSurfaceCard(child: _HeaderCard(perfil: p)),
    const SizedBox(height: 12),
    AppSurfaceCard(child: _Estatisticas(...)),
    const SizedBox(height: 12),
    _Secao(...),
  ],
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/features/estoque/estoque_screen_test.dart test/features/perfil/perfil_screen_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/features/estoque/estoque_screen.dart apps/tecnico-mobile/lib/features/perfil/perfil_screen.dart apps/tecnico-mobile/lib/features/perfil/perfil_data.dart apps/tecnico-mobile/test/features/estoque/estoque_screen_test.dart apps/tecnico-mobile/test/features/perfil/perfil_screen_test.dart
git commit -m "feat: refine estoque and perfil for iphone visual refresh"
```

### Task 6: Estados vazios, loading, offline e validação final

**Files:**
- Modify: `apps/tecnico-mobile/lib/features/os/os_list_screen.dart`
- Modify: `apps/tecnico-mobile/lib/features/clientes/clientes_list_screen.dart`
- Modify: `apps/tecnico-mobile/lib/features/estoque/estoque_screen.dart`
- Modify: `apps/tecnico-mobile/lib/features/perfil/perfil_screen.dart`
- Modify: `apps/tecnico-mobile/README.md`

- [ ] **Step 1: Add a visual polish checklist to the affected screens**

```dart
// replace plain error blocks with shared premium empty/error states
class AppStatePanel extends StatelessWidget {
  final IconData icon;
  final String title;
  final String message;
  final VoidCallback? onRetry;
}
```

- [ ] **Step 2: Run focused tests before final verification**

Run: `flutter test test/features/os/os_home_screen_test.dart test/features/clientes/cliente_visual_test.dart test/features/estoque/estoque_screen_test.dart test/features/perfil/perfil_screen_test.dart`
Expected: PASS

- [ ] **Step 3: Run full verification**

Run: `flutter test`
Expected: PASS

Run: `flutter analyze --no-fatal-infos`
Expected: no new warnings introduced by the visual refresh

- [ ] **Step 4: Update README screenshots/status notes if needed**

```md
- iPhone visual refresh with premium home-first dashboard
- refined bottom navigation and shared visual system
- consistent loading/offline/empty states
```

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/features/os/os_list_screen.dart apps/tecnico-mobile/lib/features/clientes/clientes_list_screen.dart apps/tecnico-mobile/lib/features/estoque/estoque_screen.dart apps/tecnico-mobile/lib/features/perfil/perfil_screen.dart apps/tecnico-mobile/README.md
git commit -m "feat: complete tecnico mobile iphone visual refresh"
```
