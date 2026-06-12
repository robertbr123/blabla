# iOS 26 Fase 0 (Fundação) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Elevar o look base de todas as telas pro iOS 26 reestilizando só o tema (`buildBrandTheme`) e o card compartilhado (`AppSurfaceCard`).

**Architecture:** Duas mudanças que propagam sozinhas: (1) `brand_theme.dart` — fundo agrupado cinza, card raio 20 sem borda, botões/inputs mais arredondados, helper `iosLargeTitle`; (2) `app_surfaces.dart` — `AppSurfaceCard` vira card iOS grouped sólido com sombra suave, preservando o clip. Nenhuma tela é tocada — todas herdam.

**Tech Stack:** Flutter (Material 3), Google Fonts (Inter), `ThemeData`/`ColorScheme`.

> **Nota de ambiente:** sem Flutter local — `flutter test`/`flutter analyze` rodam na máquina de deploy/CI. Passos "rodar teste" executam lá; localmente a verificação é por revisão. Commits frequentes mesmo assim. Commitar SEMPRE com `git commit --no-verify` (hook agrega arquivos de dashboard não relacionados).

---

## File Structure

- **Modify:** `lib/core/branding/brand_theme.dart` — ColorSchemes (surface), cardTheme, button themes, inputDecorationTheme, + função `iosLargeTitle`.
- **Modify:** `lib/core/ui/app_surfaces.dart` — `AppSurfaceCard`.
- **Create:** `test/core/branding/ios26_foundation_test.dart` — testes do tema + card.
- **Não muda:** nenhum arquivo em `features/**`, `MainShell`, navbar, `BrandTokens`, `core/theme.dart`.

---

### Task 1: Testes da fundação iOS 26

**Files:**
- Test (create): `test/core/branding/ios26_foundation_test.dart`

- [ ] **Step 1: Escrever os testes**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/branding/brand_theme.dart';
import 'package:tecnico_mobile/core/ui/app_surfaces.dart';

void main() {
  test('tema claro usa fundo agrupado iOS (#F2F2F7) com card branco', () {
    final scheme = buildBrandTheme(Brightness.light).colorScheme;
    expect(scheme.surface, const Color(0xFFF2F2F7));
    expect(scheme.surfaceContainer, const Color(0xFFFFFFFF));
  });

  test('tema escuro aprofunda o fundo agrupado', () {
    final scheme = buildBrandTheme(Brightness.dark).colorScheme;
    expect(scheme.surface, const Color(0xFF0B1120));
  });

  test('cardTheme usa raio 20 sem borda dura', () {
    final card = buildBrandTheme(Brightness.light).cardTheme;
    final shape = card.shape! as RoundedRectangleBorder;
    expect(shape.borderRadius, BorderRadius.circular(20));
    expect(shape.side, BorderSide.none);
  });

  test('iosLargeTitle tem tamanho e peso de large title', () {
    final scheme = buildBrandTheme(Brightness.light).colorScheme;
    final style = iosLargeTitle(scheme);
    expect(style.fontSize, 30);
    expect(style.fontWeight, FontWeight.w800);
    expect(style.color, scheme.onSurface);
  });

  testWidgets('AppSurfaceCard é card grouped (raio 20 + sombra) com clip',
      (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBrandTheme(Brightness.light),
        home: const Scaffold(body: AppSurfaceCard(child: Text('x'))),
      ),
    );

    expect(find.text('x'), findsOneWidget);

    final decorated = tester.widget<DecoratedBox>(
      find
          .descendant(
            of: find.byType(AppSurfaceCard),
            matching: find.byType(DecoratedBox),
          )
          .first,
    );
    final decoration = decorated.decoration as BoxDecoration;
    expect(decoration.borderRadius, BorderRadius.circular(20));
    expect(decoration.boxShadow, isNotEmpty);

    expect(
      find.descendant(
        of: find.byType(AppSurfaceCard),
        matching: find.byType(ClipRRect),
      ),
      findsOneWidget,
    );
  });
}
```

- [ ] **Step 2: Rodar (na máquina com Flutter) e ver falhar**

Run: `flutter test test/core/branding/ios26_foundation_test.dart`
Expected: FALHA — `surface` ainda é `#FFFFFF`, `cardTheme` raio 12 com borda, `iosLargeTitle` não existe (erro de compilação no símbolo `iosLargeTitle`), `AppSurfaceCard` ainda é `Card`.

- [ ] **Step 3: Commit**

```bash
git add test/core/branding/ios26_foundation_test.dart
git commit --no-verify -m "test(tecnico-mobile): contrato da fundação iOS 26 (tema + card)"
```

---

### Task 2: Tema iOS 26 (`brand_theme.dart`)

**Files:**
- Modify: `lib/core/branding/brand_theme.dart`

- [ ] **Step 1: Fundo agrupado no `_lightScheme`**

Em `const _lightScheme = ColorScheme(`, trocar a linha:
```dart
  surface: Color(0xFFFFFFFF),
```
por:
```dart
  surface: Color(0xFFF2F2F7), // iOS systemGroupedBackground (light)
```
(NÃO mexer em `surfaceContainer`, `surfaceContainerLowest` etc — cards seguem brancos.)

- [ ] **Step 2: Fundo agrupado no `_darkScheme`**

Em `const _darkScheme = ColorScheme(`, trocar a linha:
```dart
  surface: Color(0xFF0F172A), // slate-900
```
por:
```dart
  surface: Color(0xFF0B1120), // grouped background mais fundo (dark)
```
(NÃO mexer em `surfaceContainer: Color(0xFF1E293B)` — card.)

- [ ] **Step 3: `cardTheme` raio 20 sem borda**

Trocar todo o bloco `cardTheme:`:
```dart
    cardTheme: CardThemeData(
      color: scheme.surfaceContainer,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: scheme.outlineVariant),
      ),
    ),
```
por:
```dart
    cardTheme: CardThemeData(
      color: scheme.surfaceContainer,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
      ),
    ),
```

- [ ] **Step 4: Raios de botões e inputs**

No `filledButtonTheme` e `outlinedButtonTheme`, trocar `BorderRadius.circular(10)` por `BorderRadius.circular(14)` (uma ocorrência em cada). No `textButtonTheme`, trocar `BorderRadius.circular(8)` por `BorderRadius.circular(10)`. No `inputDecorationTheme`, trocar as TRÊS ocorrências de `BorderRadius.circular(10)` (em `border`, `enabledBorder`, `focusedBorder`) por `BorderRadius.circular(12)`. Nenhuma outra propriedade muda.

- [ ] **Step 5: Adicionar `iosLargeTitle`**

Logo após a função `tabularStyle` (antes do comentário `// ── ColorSchemes ──`), adicionar:
```dart
/// Large title estilo iOS 26 — usado nos headers das telas (fases por-tela).
TextStyle iosLargeTitle(ColorScheme scheme) => GoogleFonts.inter(
      fontSize: 30,
      fontWeight: FontWeight.w800,
      letterSpacing: -0.5,
      height: 1.1,
      color: scheme.onSurface,
    );
```

- [ ] **Step 6: Rodar testes (na máquina com Flutter)**

Run: `flutter test test/core/branding/ios26_foundation_test.dart`
Expected: passam os 4 testes de tema (`surface` light/dark, `cardTheme`, `iosLargeTitle`). O teste de `AppSurfaceCard` ainda FALHA (vem na Task 3).

- [ ] **Step 7: Commit**

```bash
git add lib/core/branding/brand_theme.dart
git commit --no-verify -m "feat(tecnico-mobile): tema iOS 26 — fundo agrupado, card raio 20, botões/inputs, iosLargeTitle"
```

---

### Task 3: `AppSurfaceCard` iOS grouped (`app_surfaces.dart`)

**Files:**
- Modify: `lib/core/ui/app_surfaces.dart`

- [ ] **Step 1: Reescrever `AppSurfaceCard`**

Substituir TODO o conteúdo de `lib/core/ui/app_surfaces.dart` por:
```dart
import 'package:flutter/material.dart';

class AppSurfaceCard extends StatelessWidget {
  const AppSurfaceCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  static const _radius = 20.0;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(_radius),
        boxShadow: [
          BoxShadow(
            color: scheme.shadow.withValues(alpha: isDark ? 0.0 : 0.06),
            blurRadius: 12,
            offset: const Offset(0, 4),
            spreadRadius: -2,
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(_radius),
        child: ColoredBox(
          color: scheme.surfaceContainer,
          child: Padding(padding: padding, child: child),
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Rodar testes (na máquina com Flutter)**

Run: `flutter test test/core/branding/ios26_foundation_test.dart`
Expected: TODOS os 5 testes passam.

- [ ] **Step 3: Rodar a suíte de UI existente (regressão)**

Run: `flutter test test/core/ui/`
Expected: passa. (O teste `surface card reuses the shared card theme` em `app_visual_system_test.dart` busca `find.byType(Card)` dentro de `AppSurfaceCard` — com a reescrita NÃO há mais `Card`. Se esse teste quebrar, é esperado: atualizar a asserção para a nova estrutura — `find.byType(AppSurfaceCard)` + `find.text('Conteudo')` + um `DecoratedBox` com `BoxDecoration` raio 20 —, mantendo o espírito do teste; commitar junto.)

- [ ] **Step 4: Commit**

```bash
git add lib/core/ui/app_surfaces.dart test/core/ui/app_visual_system_test.dart
git commit --no-verify -m "feat(tecnico-mobile): AppSurfaceCard iOS grouped (raio 20 + sombra suave)"
```

---

### Task 4: Verificação (analyze + visual on-device)

**Files:** nenhum.

- [ ] **Step 1: Analyze (na máquina com Flutter)**

Run: `flutter analyze lib/core/branding/brand_theme.dart lib/core/ui/app_surfaces.dart test/core/branding/ios26_foundation_test.dart`
Expected: `No issues found!`

- [ ] **Step 2: Verificação visual on-device**

Rodar o app e confirmar, claro e escuro:
- fundo das telas vira cinza agrupado (claro) / mais fundo (escuro);
- cards brancos arredondados (raio 20) destacando do fundo, com sombra suave no claro;
- botões/inputs com cantos mais arredondados;
- nenhuma tela quebrada (texto/contraste ok); telas que ainda parecem "brancas demais" são as que fixam `surfaceContainerLowest` — anotar pra limpar nas fases por-tela.

---

## Self-Review

**Spec coverage:**
- Light surface `#F2F2F7` → Task 2 Step 1 + teste. ✅
- Dark surface `#0B1120` → Task 2 Step 2 + teste. ✅
- cardTheme raio 20 sem borda → Task 2 Step 3 + teste. ✅
- Botões 14 / inputs 12 / textButton 10 → Task 2 Step 4. ✅
- `iosLargeTitle` helper → Task 2 Step 5 + teste. ✅
- `AppSurfaceCard` grouped sólido c/ sombra + clip preservado → Task 3 + teste. ✅
- Nenhuma tela tocada → só `brand_theme.dart`/`app_surfaces.dart` modificados. ✅
- Risco do teste de regressão `app_visual_system_test` (procura `Card` dentro de `AppSurfaceCard`) → tratado em Task 3 Step 3. ✅

**Placeholder scan:** sem TBD/TODO; todo passo tem código/edição completa. ✅

**Type consistency:** `iosLargeTitle(ColorScheme)` usado igual no teste e na definição; `AppSurfaceCard(child, padding)` mantém API; `_radius` const reutilizado no DecoratedBox e no ClipRRect. ✅
