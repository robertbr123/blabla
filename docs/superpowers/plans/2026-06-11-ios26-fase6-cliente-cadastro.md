# iOS 26 Fase 6 (Cliente cadastro) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** iOS 26 no cadastro de cliente via um AppBar de vidro não-sliver (`IosGlassAppBar`) reutilizável, sem tocar no Stepper/form.

**Architecture:** Novo `IosGlassAppBar` (PreferredSizeWidget) em `lib/core/ui/`. `cliente_novo_screen.dart` troca o `AppBar` por ele e o fundo p/ `scheme.surface`.

**Tech Stack:** Flutter (Material 3), `dart:ui` `ImageFilter.blur`, `AppBar`/`PreferredSizeWidget`.

> **Ambiente:** sem Flutter local — analyze no deploy. Commit `--no-verify`. Stay on `main`.

---

## File Structure
- **Create:** `lib/core/ui/ios_glass_app_bar.dart` — `IosGlassAppBar`.
- **Create:** `test/core/ui/ios_glass_app_bar_test.dart`.
- **Modify:** `lib/features/clientes/cliente_novo_screen.dart` — bg + AppBar.

---

### Task 1: `IosGlassAppBar`

**Files:**
- Create: `lib/core/ui/ios_glass_app_bar.dart`
- Test: `test/core/ui/ios_glass_app_bar_test.dart`

- [ ] **Step 1: Teste**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/branding/brand_theme.dart';
import 'package:tecnico_mobile/core/ui/ios_glass_app_bar.dart';

void main() {
  testWidgets('mostra título, ação e tem vidro (BackdropFilter)',
      (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBrandTheme(Brightness.light),
        home: Scaffold(
          appBar: IosGlassAppBar(
            title: 'Novo cliente',
            actions: [
              IconButton(icon: const Icon(Icons.gps_fixed), onPressed: () {}),
            ],
          ),
          body: const SizedBox(),
        ),
      ),
    );
    expect(find.text('Novo cliente'), findsOneWidget);
    expect(find.byIcon(Icons.gps_fixed), findsOneWidget);
    expect(find.byType(BackdropFilter), findsOneWidget);
  });
}
```

- [ ] **Step 2: Rodar e ver falhar (deploy)** — `IosGlassAppBar` não existe.

- [ ] **Step 3: Implementar**

Criar `lib/core/ui/ios_glass_app_bar.dart`:
```dart
import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

/// AppBar de vidro estilo iOS 26 — versão `PreferredSizeWidget`, pra telas que
/// NÃO usam CustomScrollView/sliver (forms, Stepper, etc). Irmão não-sliver do
/// `IosGlassHeader`. Em telas com CustomScrollView, prefira o `IosGlassHeader`.
class IosGlassAppBar extends StatelessWidget implements PreferredSizeWidget {
  const IosGlassAppBar({
    super.key,
    required this.title,
    this.actions = const [],
    this.leading,
    this.showBackButton = true,
  });

  final String title;
  final List<Widget> actions;
  final Widget? leading;
  final bool showBackButton;

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
        child: AppBar(
          backgroundColor: scheme.surface.withValues(alpha: 0.7),
          surfaceTintColor: Colors.transparent,
          elevation: 0,
          scrolledUnderElevation: 0,
          automaticallyImplyLeading: showBackButton,
          leading: leading,
          titleSpacing: 16,
          title: Text(
            title,
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.3,
              color: scheme.onSurface,
            ),
          ),
          actions: actions,
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: Rodar testes (deploy)** — `flutter test test/core/ui/ios_glass_app_bar_test.dart` → PASS.
- [ ] **Step 5: Commit**

```bash
git add lib/core/ui/ios_glass_app_bar.dart test/core/ui/ios_glass_app_bar_test.dart
git commit --no-verify -m "feat(tecnico-mobile): IosGlassAppBar (AppBar de vidro PreferredSizeWidget)"
```

---

### Task 2: Cadastro usa o IosGlassAppBar

**Files:** Modify `lib/features/clientes/cliente_novo_screen.dart`

- [ ] **Step 1: Import**

Adicionar junto aos imports de `core/ui`:
```dart
import '../../core/ui/ios_glass_app_bar.dart';
```

- [ ] **Step 2: Trocar bg + AppBar**

Substituir:
```dart
    return Scaffold(
      backgroundColor: scheme.surfaceContainerLowest,
      appBar: AppBar(
        title: const Text('Novo cliente'),
        actions: [
          // Status do GPS no header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Center(child: _GpsChip(gps: _gps, capturing: _gpsCapturing)),
          ),
        ],
      ),
```
por:
```dart
    return Scaffold(
      backgroundColor: scheme.surface,
      appBar: IosGlassAppBar(
        title: 'Novo cliente',
        actions: [
          // Status do GPS no header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Center(child: _GpsChip(gps: _gps, capturing: _gpsCapturing)),
          ),
        ],
      ),
```
(O `body: SafeArea(Column[...])` e todo o resto ficam IGUAIS.)

- [ ] **Step 3: Analyze (deploy)**

Run: `flutter analyze lib/features/clientes/cliente_novo_screen.dart lib/core/ui/ios_glass_app_bar.dart`
Expected: `No issues found!`.

- [ ] **Step 4: Commit**

```bash
git add lib/features/clientes/cliente_novo_screen.dart
git commit --no-verify -m "feat(tecnico-mobile): Cliente cadastro com IosGlassAppBar (iOS 26)"
```

---

### Task 3: Verificação

- [ ] **Step 1: Analyze (deploy)** — `flutter analyze lib/features/clientes/cliente_novo_screen.dart lib/core/ui/ios_glass_app_bar.dart` → limpo.
- [ ] **Step 2: Visual on-device (claro/escuro):**
  - barra "Novo cliente" translúcida com voltar + chip GPS; fundo cinza agrupado;
  - os 3 passos do Stepper, validações, ViaCEP, GPS, materiais e o envio funcionam idênticos;
  - inputs/botões arredondados (Fase 0); voltar cancela o cadastro normalmente.

---

## Self-Review

**Spec coverage:**
- `IosGlassAppBar` PreferredSizeWidget (blur + título 20/w800 + back + actions) → Task 1. ✅
- Cadastro: bg `surfaceContainerLowest`→`surface`, AppBar→IosGlassAppBar com o mesmo chip GPS → Task 2. ✅
- Stepper/form/lógica intactos → Task 2 só toca bg + appBar. ✅
- Reutilizável p/ Rede/Login → componente sem acoplamento. ✅

**Placeholder scan:** sem TBD; código completo.

**Type consistency:** `IosGlassAppBar` implements `PreferredSizeWidget` (Scaffold.appBar aceita); `actions: List<Widget>`; `_GpsChip`/`_gps`/`_gpsCapturing` continuam no escopo da State.
