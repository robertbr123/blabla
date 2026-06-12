# iOS 26 — Fase 0: Fundação — Design

**Data:** 2026-06-11
**App:** `apps/tecnico-mobile` (Flutter — técnico em campo)
**Tema ativo:** `buildBrandTheme` em `lib/core/branding/brand_theme.dart` (confirmado: `main.dart` usa este; `core/theme.dart` é legado e não é usado em `lib/`).

## Contexto e objetivo

Levar o app inteiro pro visual iOS 26 ("liquid glass" + grouped). Como toda tela
consome o **tema** e o **card compartilhado** (`AppSurfaceCard`), a Fase 0 reestiliza
só esses dois pontos e já eleva o look base de TODAS as telas de uma vez:
fundo agrupado cinza, cards brancos arredondados com sombra suave, botões/inputs
mais arredondados.

Direção visual aprovada via mockup. Política aprovada: **vidro só no chrome
(navbar/headers/sheets), cards sólidos** — que é o que o iOS faz de verdade
(mais autêntico e mais leve em Android de campo).

A navbar liquid glass já foi entregue e faz parte deste sistema.

## Escopo da Fase 0

**Muda apenas:**
- `lib/core/branding/brand_theme.dart` — ColorSchemes (fundo agrupado), `cardTheme`,
  `filledButtonTheme`/`outlinedButtonTheme`/`textButtonTheme`, `inputDecorationTheme`,
  + helper `iosLargeTitle` (TextStyle reutilizável pros headers das próximas fases).
- `lib/core/ui/app_surfaces.dart` — `AppSurfaceCard` vira o card iOS grouped.

**NÃO muda (fica pras fases por-tela):** large-title headers de vidro, segmented
controls, reagrupamento de conteúdo, limpeza de `backgroundColor` hardcoded nas telas.

**NÃO toca:** nenhum arquivo de tela (`features/**`), `MainShell`, navbar, `BrandTokens`,
`core/theme.dart` (legado).

## Mudanças de tema (`brand_theme.dart`)

### `_lightScheme`
- `surface`: `0xFFFFFFFF` → **`0xFFF2F2F7`** (iOS systemGroupedBackground light).
  Isso torna o `scaffoldBackgroundColor` e os `AppBar` cinza-agrupado; os cards
  (que usam `surfaceContainer` = branco) passam a "flutuar" sobre o cinza.
- `surfaceContainer` permanece **`0xFFFFFFFF`** (card branco) — inalterado.
- `surfaceContainerLowest` permanece `0xFFFFFFFF`; `surfaceContainerLow` permanece
  `0xFFF8FAFC` (fill de input). Demais valores inalterados.

### `_darkScheme`
- `surface`: `0xFF0F172A` → **`0xFF0B1120`** (um tom mais fundo p/ separar do card).
- `surfaceContainer` permanece `0xFF1E293B` (card). Demais inalterados.
  (Dark já era grouped; mudança mínima e conservadora.)

### `cardTheme`
De:
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
Para:
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
(raio 12 → 20, remove a borda dura. A sombra suave vem do `AppSurfaceCard`.)

### Botões e inputs
- `filledButtonTheme`: raio `10` → **`14`**.
- `outlinedButtonTheme`: raio `10` → **`14`**.
- `textButtonTheme`: raio `8` → **`10`**.
- `inputDecorationTheme` (`border`/`enabledBorder`/`focusedBorder`): raio `10` → **`12`**.
Nenhuma outra propriedade desses temas muda (cores, padding, foco etc. ficam).

### Helper de tipografia (novo, reutilizável)
Adicionar (perto de `tabularStyle`):
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
(Definido na Fase 0, consumido nas fases por-tela. Inter é mantido — SF é proprietária.)

## `AppSurfaceCard` (`app_surfaces.dart`)

Vira o card iOS grouped: sólido, raio 20, sombra suave, **mantendo o clip**
arredondado do conteúdo (o `Card` atual usa `Clip.antiAlias`).

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
Notas:
- Sombra fica no `DecoratedBox` externo (o `ClipRRect` interno cortaria); o clip
  preserva o comportamento `Clip.antiAlias` do `Card` antigo (conteúdo com imagem
  nos cantos continua arredondado).
- Em dark a sombra é transparente (iOS dark separa por cor, não por sombra).
- API pública (`child`, `padding`) inalterada — nenhum call-site muda.

## Critérios de sucesso

1. `buildBrandTheme(Brightness.light).colorScheme.surface == Color(0xFFF2F2F7)`.
2. `buildBrandTheme(...).cardTheme.shape` é `RoundedRectangleBorder` raio 20 **sem** `side`.
3. `AppSurfaceCard` renderiza com raio 20 e sombra suave (light), preservando o clip.
4. Todas as telas existentes continuam compilando sem alteração (só herdam o tema).
5. `flutter analyze` limpo (validado na máquina de deploy — sem stack local aqui).
6. Visual on-device: fundo cinza agrupado no claro, cards brancos arredondados
   destacando do fundo; botões/inputs mais arredondados; nada quebrado.

## Riscos conhecidos

- Telas que fixam `backgroundColor: scheme.surface` passam a cinza (desejado);
  as que fixam `surfaceContainerLowest` (branco) podem destoar pontualmente —
  **limpeza dessas vai nas fases por-tela**, não na Fase 0.
- `core/theme.dart` (legado, navy) não é tocado; o teste existente
  `app_visual_system_test.dart` aponta pra ele e segue válido.
