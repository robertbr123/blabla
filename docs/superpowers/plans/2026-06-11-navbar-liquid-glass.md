# Navbar Liquid Glass — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformar o `BrandBottomNav` num navbar liquid glass (pill flutuante translúcido com `BackdropFilter` + lente de vidro especular deslizante), sem tocar na API do componente nem no `MainShell`.

**Architecture:** Reescrita interna do widget `BrandBottomNav` em `lib/core/branding/brand_bottom_nav.dart`. A casca de vidro = `DecoratedBox` (sombra externa) → `ClipRRect` → `BackdropFilter(blur)` → `DecoratedBox` (gradiente translúcido + borda). A bolha de seleção atual vira um `_GlassLens` dentro do `AnimatedPositioned` já existente. Cores de destaque saem de `scheme.primary` (emerald nos dois temas), então dark mode funciona sozinho.

**Tech Stack:** Flutter (Material 3), `dart:ui` `ImageFilter.blur`, Riverpod (não afetado).

> **Nota de ambiente:** este projeto não roda Flutter localmente — `flutter test`/`flutter analyze` rodam na máquina de deploy/CI após o push. Os passos "rodar teste" abaixo são executados lá; localmente a verificação é por revisão de código. Commits são frequentes mesmo assim.

---

## File Structure

- **Modify:** `lib/core/branding/brand_bottom_nav.dart` — reescrita do `build()` de `BrandBottomNav` + novo widget privado `_GlassLens`. `BrandNavItem` e `_NavSlot` praticamente inalterados.
- **Create:** `test/core/branding/brand_bottom_nav_test.dart` — testes de contrato de comportamento + presença das novas estruturas (glass, lente).
- **Não muda:** `lib/features/shell/main_shell.dart`, `BrandNavItem`, API pública (`selectedIndex`, `onSelect`, `items`).

---

### Task 1: Testes de contrato do BrandBottomNav

**Files:**
- Test (create): `test/core/branding/brand_bottom_nav_test.dart`

- [ ] **Step 1: Escrever os testes**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/branding/brand_bottom_nav.dart';
import 'package:tecnico_mobile/core/branding/brand_theme.dart';

const _items = [
  BrandNavItem(
      icon: Icons.assignment_outlined,
      selectedIcon: Icons.assignment_rounded,
      label: 'OS'),
  BrandNavItem(
      icon: Icons.inventory_2_outlined,
      selectedIcon: Icons.inventory_2_rounded,
      label: 'Estoque'),
  BrandNavItem(
      icon: Icons.people_outline,
      selectedIcon: Icons.people_rounded,
      label: 'Clientes'),
  BrandNavItem(
      icon: Icons.person_outline,
      selectedIcon: Icons.person_rounded,
      label: 'Perfil'),
];

Future<void> _pump(
  WidgetTester tester, {
  required int selected,
  required void Function(int) onSelect,
  Brightness brightness = Brightness.light,
}) {
  return tester.pumpWidget(
    MaterialApp(
      theme: buildBrandTheme(brightness),
      home: Scaffold(
        bottomNavigationBar: BrandBottomNav(
          selectedIndex: selected,
          onSelect: onSelect,
          items: _items,
        ),
      ),
    ),
  );
}

void main() {
  testWidgets('renderiza um slot com label por item', (tester) async {
    await _pump(tester, selected: 0, onSelect: (_) {});
    for (final it in _items) {
      expect(find.text(it.label), findsOneWidget);
    }
  });

  testWidgets('tocar em aba não-selecionada chama onSelect com o índice',
      (tester) async {
    int? picked;
    await _pump(tester, selected: 0, onSelect: (i) => picked = i);
    await tester.tap(find.text('Clientes'));
    await tester.pump();
    expect(picked, 2);
  });

  testWidgets('tocar na aba já selecionada não chama onSelect',
      (tester) async {
    var calls = 0;
    await _pump(tester, selected: 0, onSelect: (_) => calls++);
    await tester.tap(find.text('OS'));
    await tester.pump();
    expect(calls, 0);
  });

  testWidgets('aba selecionada expõe Semantics selected=true', (tester) async {
    await _pump(tester, selected: 2, onSelect: (_) {});
    final handle = tester.ensureSemantics();
    expect(
      tester.getSemantics(find.text('Clientes')),
      matchesSemantics(label: 'Clientes', isSelected: true, isButton: true),
    );
    handle.dispose();
  });

  testWidgets('aplica vidro com BackdropFilter', (tester) async {
    await _pump(tester, selected: 0, onSelect: (_) {});
    expect(find.byType(BackdropFilter), findsOneWidget);
  });

  testWidgets('tem a lente deslizante (AnimatedPositioned)', (tester) async {
    await _pump(tester, selected: 1, onSelect: (_) {});
    expect(find.byType(AnimatedPositioned), findsOneWidget);
  });
}
```

- [ ] **Step 2: Rodar (na máquina com Flutter) e ver falhar**

Run: `flutter test test/core/branding/brand_bottom_nav_test.dart`
Expected: o teste `aplica vidro com BackdropFilter` FALHA (o widget atual não tem `BackdropFilter`). Os demais passam (comportamento já existe). Isso confirma o ponto de partida da reescrita.

- [ ] **Step 3: Commit**

```bash
git add test/core/branding/brand_bottom_nav_test.dart
git commit --no-verify -m "test(tecnico-mobile): contrato do BrandBottomNav antes do liquid glass"
```

---

### Task 2: Casca de vidro (BackdropFilter + gradiente translúcido)

Reescreve o `build()` mantendo a bolha antiga por enquanto (continua compilando e os testes de comportamento seguem passando). Só a casca vira vidro.

**Files:**
- Modify: `lib/core/branding/brand_bottom_nav.dart`

- [ ] **Step 1: Adicionar import do `dart:ui`**

No topo do arquivo, abaixo dos imports existentes:

```dart
import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
```

- [ ] **Step 2: Atualizar as constantes da classe**

Substituir o bloco de constantes em `BrandBottomNav`:

```dart
  static const _kHeight = 60.0;
  static const _kRadius = 22.0;
  static const _kSlideDuration = Duration(milliseconds: 420);
```

por:

```dart
  static const _kHeight = 60.0;
  static const _kRadius = 26.0;
  static const _kBlurSigma = 20.0;
  static const _kSlideDuration = Duration(milliseconds: 420);
```

- [ ] **Step 3: Substituir o `build()` inteiro pela casca de vidro**

Substituir o método `build` de `BrandBottomNav` por:

```dart
  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    // Camadas translúcidas do vidro conforme o tema.
    final glassTop = isDark
        ? const Color(0xFF282E32).withValues(alpha: 0.55)
        : Colors.white.withValues(alpha: 0.55);
    final glassBottom = isDark
        ? const Color(0xFF1C2024).withValues(alpha: 0.42)
        : Colors.white.withValues(alpha: 0.32);
    final borderColor = isDark
        ? Colors.white.withValues(alpha: 0.14)
        : Colors.white.withValues(alpha: 0.70);

    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 4, 14, 10),
        child: DecoratedBox(
          // Sombra externa fica AQUI (fora do ClipRRect — o clip cortaria).
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(_kRadius),
            boxShadow: [
              BoxShadow(
                color: scheme.shadow.withValues(alpha: isDark ? 0.5 : 0.22),
                blurRadius: isDark ? 36 : 34,
                offset: const Offset(0, 12),
                spreadRadius: -2,
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(_kRadius),
            child: BackdropFilter(
              filter:
                  ImageFilter.blur(sigmaX: _kBlurSigma, sigmaY: _kBlurSigma),
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [glassTop, glassBottom],
                  ),
                  borderRadius: BorderRadius.circular(_kRadius),
                  border: Border.all(color: borderColor, width: 1),
                ),
                child: SizedBox(
                  height: _kHeight,
                  child: LayoutBuilder(builder: (context, c) {
                    final slotW = c.maxWidth / items.length;
                    return Stack(
                      children: [
                        // Bolha antiga (substituída pela lente na Task 3).
                        AnimatedPositioned(
                          duration: _kSlideDuration,
                          curve: Curves.easeOutBack,
                          left: selectedIndex * slotW + 6,
                          top: 5,
                          bottom: 5,
                          width: slotW - 12,
                          child: AnimatedContainer(
                            duration: _kSlideDuration,
                            decoration: BoxDecoration(
                              color: scheme.primary
                                  .withValues(alpha: isDark ? 0.16 : 0.10),
                              borderRadius: BorderRadius.circular(22),
                            ),
                          ),
                        ),
                        Row(
                          children: [
                            for (var i = 0; i < items.length; i++)
                              Expanded(
                                child: _NavSlot(
                                  item: items[i],
                                  selected: i == selectedIndex,
                                  onTap: () => _handleTap(i),
                                ),
                              ),
                          ],
                        ),
                      ],
                    );
                  }),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
```

- [ ] **Step 4: Rodar testes (na máquina com Flutter)**

Run: `flutter test test/core/branding/brand_bottom_nav_test.dart`
Expected: TODOS passam agora (inclusive `aplica vidro com BackdropFilter` e `tem a lente deslizante`).

- [ ] **Step 5: Commit**

```bash
git add lib/core/branding/brand_bottom_nav.dart
git commit --no-verify -m "feat(tecnico-mobile): casca de vidro (BackdropFilter) no BrandBottomNav"
```

---

### Task 3: Lente de vidro especular deslizante

Troca a `AnimatedContainer` da bolha pelo widget `_GlassLens`.

**Files:**
- Modify: `lib/core/branding/brand_bottom_nav.dart`

- [ ] **Step 1: Substituir o filho do `AnimatedPositioned` pela lente**

No `build()` (Task 2 Step 3), trocar o bloco:

```dart
                          child: AnimatedContainer(
                            duration: _kSlideDuration,
                            decoration: BoxDecoration(
                              color: scheme.primary
                                  .withValues(alpha: isDark ? 0.16 : 0.10),
                              borderRadius: BorderRadius.circular(22),
                            ),
                          ),
```

por:

```dart
                          child: _GlassLens(scheme: scheme, isDark: isDark),
```

- [ ] **Step 2: Adicionar o widget `_GlassLens`**

No fim do arquivo (depois da classe `_NavSlot`), adicionar:

```dart
/// Lente de vidro especular do item ativo — desliza entre os slots.
/// Claro: vidro branco brilhante com glow emerald. Escuro: vidro tintado emerald.
class _GlassLens extends StatelessWidget {
  final ColorScheme scheme;
  final bool isDark;

  const _GlassLens({required this.scheme, required this.isDark});

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: isDark
              ? [
                  scheme.primary.withValues(alpha: 0.30),
                  scheme.primary.withValues(alpha: 0.12),
                ]
              : [
                  Colors.white.withValues(alpha: 0.90),
                  Colors.white.withValues(alpha: 0.40),
                ],
        ),
        border: Border.all(
          color: isDark
              ? scheme.primary.withValues(alpha: 0.50)
              : Colors.white.withValues(alpha: 0.95),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: scheme.primary.withValues(alpha: isDark ? 0.35 : 0.30),
            blurRadius: 12,
            spreadRadius: -2,
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 3: Rodar testes (na máquina com Flutter)**

Run: `flutter test test/core/branding/brand_bottom_nav_test.dart`
Expected: todos passam (a lente continua sendo um `AnimatedPositioned`; trocamos só o filho).

- [ ] **Step 4: Commit**

```bash
git add lib/core/branding/brand_bottom_nav.dart
git commit --no-verify -m "feat(tecnico-mobile): lente de vidro especular deslizante no navbar"
```

---

### Task 4: Verificação (analyze + visual on-device)

**Files:** nenhum (verificação).

- [ ] **Step 1: Confirmar contraste do item inativo sobre o vidro**

Ler `_NavSlot.build`: a cor inativa é `scheme.onSurfaceVariant` (slate-500 `#64748B` claro / slate-400 `#94A3B8` escuro). Sobre o vidro branco/grafite o contraste é suficiente. Nenhuma mudança necessária — apenas confirmar que `_NavSlot` continua usando `final fg = selected ? scheme.primary : scheme.onSurfaceVariant;`.

- [ ] **Step 2: Analyze (na máquina com Flutter)**

Run: `flutter analyze lib/core/branding/brand_bottom_nav.dart test/core/branding/brand_bottom_nav_test.dart`
Expected: `No issues found!`

- [ ] **Step 3: Verificação visual on-device**

Rodar o app no aparelho e confirmar, nos temas claro e escuro:
- a barra fica translúcida com o conteúdo borrado por trás ao rolar a lista;
- a lente desliza suave entre as 4 abas ao trocar;
- ícone-pop, peso do label e haptic continuam funcionando;
- o FAB "Novo" (aba Clientes) não colide visualmente com a barra.

- [ ] **Step 4: Commit final (se houve ajuste de contraste)**

```bash
git add lib/core/branding/brand_bottom_nav.dart
git commit --no-verify -m "polish(tecnico-mobile): ajuste de contraste do navbar glass"
```

---

## Self-Review

**Spec coverage:**
- Forma C (pill flutuante translúcido) → Task 2. ✅
- BackdropFilter dentro de ClipRRect, sombra fora → Task 2 Step 3. ✅
- Gradiente claro/escuro + borda hairline → Task 2. ✅
- Lente especular deslizante (claro branco / escuro emerald) → Task 3. ✅
- Mantém AnimatedPositioned 420ms easeOutBack → Task 2/3. ✅
- Ícone-pop, label weight, haptic, Semantics → preservados (`_NavSlot`/`_handleTap` inalterados); cobertos por testes Task 1. ✅
- API e MainShell intactos → nenhum arquivo deles é modificado. ✅
- Fallback de blur: NÃO implementado agora (YAGNI, conforme spec). ✅

**Desvio consciente do spec:** o spec citava hex `#047857`/`#34d399` pro ativo; o plano usa `scheme.primary` (emerald `#10B981` claro / `#34D399` escuro) — mesma intenção visual (emerald), porém theme-aware e sem hardcode. Inset-highlight do topo da barra omitido (Border.all uniforme) — polish opcional, não essencial ao look aprovado.

**Placeholder scan:** sem TBD/TODO; todo passo tem código completo. ✅

**Type consistency:** `_GlassLens({required ColorScheme scheme, required bool isDark})` usado consistentemente; `BrandNavItem`/`_NavSlot` inalterados. ✅
