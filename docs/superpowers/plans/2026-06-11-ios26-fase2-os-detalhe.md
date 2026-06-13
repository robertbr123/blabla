# iOS 26 Fase 2 (OS detalhe) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Aplicar iOS 26 na OS detalhe reusando o `IosGlassHeader` (estendido com botão voltar) e convertendo o corpo pra `CustomScrollView`.

**Architecture:** `IosGlassHeader` ganha `showBackButton`. `os_detail_screen.dart` troca `AppBar`+`ListView` por `CustomScrollView` com o header de vidro + conteúdo em slivers; fundo vira `scheme.surface`.

**Tech Stack:** Flutter (Material 3), `SliverAppBar`, `SliverFillRemaining`/`SliverToBoxAdapter`.

> **Ambiente:** sem Flutter local — `flutter test`/`analyze` no deploy. Commitar SEMPRE com `git commit --no-verify`. Stay on `main`.

---

## File Structure
- **Modify:** `lib/core/ui/ios_glass_header.dart` — add `showBackButton`.
- **Modify:** `test/core/ui/ios_glass_header_test.dart` — add back-button test.
- **Modify:** `lib/features/os/os_detail_screen.dart` — header de vidro + slivers + fundo.

---

### Task 1: `IosGlassHeader.showBackButton`

**Files:**
- Modify: `lib/core/ui/ios_glass_header.dart`
- Test: `test/core/ui/ios_glass_header_test.dart`

- [ ] **Step 1: Adicionar o teste do back button**

Em `test/core/ui/ios_glass_header_test.dart`, dentro do `main()`, adicionar este teste (depois do existente):
```dart
  testWidgets('showBackButton exibe voltar quando há rota pra popar',
      (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBrandTheme(Brightness.light),
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => const Scaffold(
                    body: CustomScrollView(
                      slivers: [
                        IosGlassHeader(title: 'Detalhe', showBackButton: true),
                        SliverToBoxAdapter(child: SizedBox(height: 600)),
                      ],
                    ),
                  ),
                ),
              ),
              child: const Text('ir'),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('ir'));
    await tester.pumpAndSettle();
    expect(find.byType(BackButton), findsOneWidget);
  });
```

- [ ] **Step 2: Rodar e ver falhar (deploy)** — `IosGlassHeader` ainda não aceita `showBackButton` (erro de compilação).

- [ ] **Step 3: Implementar o parâmetro**

Em `lib/core/ui/ios_glass_header.dart`:

(a) Adicionar o campo + construtor:
```dart
  const IosGlassHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.actions = const [],
    this.showBackButton = false,
  });

  final String title;
  final String? subtitle;
  final List<Widget> actions;
  final bool showBackButton;
```

(b) No `SliverAppBar`, trocar:
```dart
      automaticallyImplyLeading: false,
```
por:
```dart
      automaticallyImplyLeading: showBackButton,
```

- [ ] **Step 4: Rodar testes (deploy)** — `flutter test test/core/ui/ios_glass_header_test.dart` → PASS (os 2 testes).

- [ ] **Step 5: Commit**

```bash
git add lib/core/ui/ios_glass_header.dart test/core/ui/ios_glass_header_test.dart
git commit --no-verify -m "feat(tecnico-mobile): IosGlassHeader com showBackButton (telas de detalhe)"
```

---

### Task 2: OS detalhe com header de vidro + slivers

**Files:**
- Modify: `lib/features/os/os_detail_screen.dart`

- [ ] **Step 1: Import do header**

Adicionar junto aos imports de `core/ui`:
```dart
import '../../core/ui/ios_glass_header.dart';
```

- [ ] **Step 2: Reescrever `OsDetailScreen.build`**

Substituir o `build` de `OsDetailScreen`:
```dart
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(osDetailProvider(id));
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: scheme.surfaceContainerLowest,
      appBar: AppBar(
        title: const Text('Detalhe da OS'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(osDetailProvider(id)),
          ),
        ],
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) =>
            _Erro(e: e, onRetry: () => ref.invalidate(osDetailProvider(id))),
        data: (os) => _Body(osId: id, os: os),
      ),
    );
  }
```
por:
```dart
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(osDetailProvider(id));
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: scheme.surface,
      body: CustomScrollView(
        slivers: [
          IosGlassHeader(
            title: 'Detalhe da OS',
            showBackButton: true,
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh),
                tooltip: 'Atualizar',
                onPressed: () => ref.invalidate(osDetailProvider(id)),
              ),
            ],
          ),
          async.when(
            loading: () => const SliverFillRemaining(
              hasScrollBody: false,
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (e, _) => SliverFillRemaining(
              hasScrollBody: false,
              child: _Erro(e: e, onRetry: () => ref.invalidate(osDetailProvider(id))),
            ),
            data: (os) => SliverToBoxAdapter(child: _Body(osId: id, os: os)),
          ),
        ],
      ),
    );
  }
```

- [ ] **Step 3: Converter o `_Body.build` de ListView pra Column**

Em `_Body.build`, trocar o `return ListView(...)`:
```dart
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      children: [
```
por:
```dart
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
```
E fechar: o `ListView` terminava com
```dart
      ],
    );
```
que vira
```dart
        ],
      ),
    );
```
(Os filhos — banner pendente, `_StatusSection`, `SizedBox`(s), `_ContextSection`, `_LocationSection` condicional, `_ActionsSection`, `_PhotosSection` — ficam EXATAMENTE iguais, só re-indentados um nível.)

- [ ] **Step 4: Rodar testes + analyze (deploy)**

Run: `flutter test test/ && flutter analyze lib/features/os/os_detail_screen.dart lib/core/ui/ios_glass_header.dart`
Expected: PASS / `No issues found!`.

- [ ] **Step 5: Commit**

```bash
git add lib/features/os/os_detail_screen.dart
git commit --no-verify -m "feat(tecnico-mobile): OS detalhe com header de vidro + voltar (iOS 26)"
```

---

### Task 3: Verificação

- [ ] **Step 1: Analyze (deploy)** — `flutter analyze lib/features/os/ lib/core/ui/ios_glass_header.dart` → limpo.
- [ ] **Step 2: Visual on-device (claro/escuro):**
  - barra de vidro "Detalhe da OS" com **voltar** (esquerda) + atualizar (direita); conteúdo rola sob o vidro;
  - fundo cinza agrupado, cards (Status/Contexto/Localização/Ações/Fotos) brancos destacando;
  - voltar funciona; iniciar/concluir/foto e a sheet de conclusão funcionam igual;
  - OS lista continua intacta (header sem voltar).

---

## Self-Review

**Spec coverage:**
- `showBackButton` no `IosGlassHeader` → Task 1. ✅
- OS detalhe com header de vidro + voltar + refresh → Task 2 Step 2. ✅
- Fundo `surfaceContainerLowest`→`surface` → Task 2 Step 2. ✅
- Conteúdo em slivers, `_Body` ListView→Column(stretch) → Task 2 Steps 2-3. ✅
- loading/erro em `SliverFillRemaining` → Task 2 Step 2. ✅
- OS lista intacta (default `showBackButton: false`) → não tocada; teste do header cobre o default. ✅

**Placeholder scan:** sem TBD; código completo. ✅

**Type consistency:** `IosGlassHeader(showBackButton: ...)` opcional default false; `_Body` continua `ConsumerWidget` com `osId`/`os`; `_Erro`/seções inalterados. ✅
