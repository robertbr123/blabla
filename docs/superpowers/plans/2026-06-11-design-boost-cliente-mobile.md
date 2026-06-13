# Design Boost — Cliente Mobile (Liquid Glass + Estados + Tokens + Microinterações) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Subir o nível visual do app cliente-mobile: navbar liquid glass (estilo WhatsApp/iOS 26), AppBars de vidro nas telas internas, componentes padronizados de loading/erro/vazio, cores hardcoded migradas pra BrandTokens, e microinterações (auto-scroll do carrossel, pressed-scale, transições de página).

**Architecture:** Tudo é refinamento de UI sobre a base existente — `BrandTokens`/`BrandTheme` (Material 3, dark mode), navbar em `floating_nav_bar.dart` (já flutuante com bolha líquida e `extendBody: true` no shell), `GlassCard` já usa `BackdropFilter` (padrão a seguir). Sem mudança de API/backend. Hero animations card→detalhe ficam ADIADAS pra Promoções Fase 2 (não existe página de destino ainda — ver spec `2026-06-11-promocoes-fase2-pagina-cta-leads-design.md`).

**Tech Stack:** Flutter 3.44 / Dart 3.6+, Riverpod 2, GoRouter 14. Verificação: `flutter analyze` (CI usa `--no-fatal-infos`: warning/error quebram, info não) e `flutter test`.

**Diretório de trabalho:** `/Users/robertalbino/Developer/blabla/apps/cliente-mobile`

**Regras de commit:** commit local por task, mensagem em pt-BR estilo do repo (`polish(app): ...`). NÃO fazer push — Robert dá o OK no final.

---

### Task 1: Navbar liquid glass

**Files:**
- Modify: `lib/features/shell/widgets/floating_nav_bar.dart`

O navbar hoje tem fundo sólido (`surface`/`surfaceDark`). Vira vidro: blur do conteúdo que rola atrás + fundo translúcido + borda-brilho + specular highlight na bolha.

- [ ] **Step 1: Adicionar import de `dart:ui` e aplicar ClipRRect + BackdropFilter**

No topo do arquivo, adicionar (mantendo o `dart:math`):

```dart
import 'dart:math' as math;
import 'dart:ui' as ui;
```

No `build` do `FloatingNavBar`, substituir o bloco do `Container` (linhas ~52-90) por:

```dart
        child: ClipRRect(
          borderRadius: BorderRadius.circular(BrandTokens.radius2xl),
          child: BackdropFilter(
            filter: ui.ImageFilter.blur(sigmaX: 24, sigmaY: 24),
            child: Container(
              decoration: BoxDecoration(
                // Translúcido: o conteúdo desfocado aparece através (liquid glass).
                color: bg.withOpacity(isDark ? 0.55 : 0.62),
                borderRadius: BorderRadius.circular(BrandTokens.radius2xl),
                border: Border.all(
                  color: isDark
                      ? Colors.white.withOpacity(0.10)
                      : Colors.white.withOpacity(0.65),
                  width: 1.2,
                ),
              ),
              padding: const EdgeInsets.symmetric(
                horizontal: BrandTokens.spaceSm,
                vertical: BrandTokens.spaceSm,
              ),
              // Stack: a bolha viaja atrás dos itens (continuidade — um único
              // elemento desliza em vez de sumir/aparecer em cada tile).
              child: Stack(
                children: [
                  Positioned.fill(
                    child: _NavBubble(
                      currentIndex: currentIndex,
                      itemCount: items.length,
                    ),
                  ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      for (int i = 0; i < items.length; i++)
                        Expanded(
                          child: _NavItemTile(
                            item: items[i],
                            selected: i == currentIndex,
                            onTap: () => onTap(i),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
```

**Atenção:** a sombra (`boxShadow: BrandTokens.elevation3`) não pode ficar dentro do `ClipRRect` (seria clipada). Envolver o `ClipRRect` num `DecoratedBox` externo que só carrega a sombra:

```dart
        child: DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(BrandTokens.radius2xl),
            boxShadow: BrandTokens.elevation3,
          ),
          child: ClipRRect(
            // ... (bloco acima)
          ),
        ),
```

- [ ] **Step 2: Specular highlight na bolha**

No `_NavBubbleState.build`, substituir o `DecoratedBox` interno (linhas ~185-195) por uma versão com brilho no topo (vidro refratando luz):

```dart
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        primary.withOpacity(isDark ? 0.26 : 0.16),
                        primary.withOpacity(isDark ? 0.12 : 0.06),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
                  ),
                  child: DecoratedBox(
                    // Specular highlight: faixa de luz no topo da bolha.
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          Colors.white.withOpacity(isDark ? 0.10 : 0.35),
                          Colors.white.withOpacity(0.0),
                        ],
                        stops: const [0.0, 0.55],
                      ),
                      borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
                    ),
                  ),
                ),
```

- [ ] **Step 3: Verificar**

Run: `flutter analyze`
Expected: sem warning/error novos (info é ok).

- [ ] **Step 4: Commit**

```bash
git add lib/features/shell/widgets/floating_nav_bar.dart
git commit -m "polish(app): navbar liquid glass — blur + translucido + specular highlight"
```

---

### Task 2: Componente GlassAppBar

**Files:**
- Create: `lib/core/ui/glass_app_bar.dart`
- Test: `test/glass_app_bar_test.dart`

AppBar de vidro reutilizável pras telas internas. Mesmo tratamento do navbar: blur + translúcido. Implementa `PreferredSizeWidget` pra ser drop-in replacement de `AppBar`.

- [ ] **Step 1: Escrever o teste (falhando)**

`test/glass_app_bar_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cliente_mobile/core/ui/glass_app_bar.dart';

void main() {
  testWidgets('GlassAppBar renderiza titulo e aplica BackdropFilter',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          extendBodyBehindAppBar: true,
          appBar: GlassAppBar(title: 'Minha Tela'),
          body: SizedBox.expand(),
        ),
      ),
    );
    expect(find.text('Minha Tela'), findsOneWidget);
    expect(find.byType(BackdropFilter), findsOneWidget);
  });

  testWidgets('GlassAppBar aceita actions', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          appBar: GlassAppBar(
            title: 'Tela',
            actions: [IconButton(icon: const Icon(Icons.add), onPressed: () {})],
          ),
          body: const SizedBox.expand(),
        ),
      ),
    );
    expect(find.byIcon(Icons.add), findsOneWidget);
  });
}
```

(Nome do package confirmado no `pubspec.yaml`: `cliente_mobile`.)

- [ ] **Step 2: Rodar o teste e ver falhar**

Run: `flutter test test/glass_app_bar_test.dart`
Expected: FAIL (arquivo `glass_app_bar.dart` não existe).

- [ ] **Step 3: Implementar o componente**

`lib/core/ui/glass_app_bar.dart`:

```dart
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import '../branding/brand_tokens.dart';

/// AppBar de vidro (liquid glass): blur do conteúdo que passa por trás +
/// fundo translúcido + linha-brilho na base. Drop-in replacement de AppBar.
/// Usar com `extendBodyBehindAppBar: true` no Scaffold pro blur ter efeito;
/// em scrollables, compensar o topo com
/// `MediaQuery.paddingOf(context).top + kToolbarHeight`.
class GlassAppBar extends StatelessWidget implements PreferredSizeWidget {
  const GlassAppBar({
    super.key,
    required this.title,
    this.actions,
    this.leading,
    this.bottom,
  });

  final String title;
  final List<Widget>? actions;
  final Widget? leading;
  final PreferredSizeWidget? bottom;

  @override
  Size get preferredSize =>
      Size.fromHeight(kToolbarHeight + (bottom?.preferredSize.height ?? 0));

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? BrandTokens.surfaceDark : BrandTokens.background;

    return ClipRect(
      child: BackdropFilter(
        filter: ui.ImageFilter.blur(sigmaX: 24, sigmaY: 24),
        child: AppBar(
          title: Text(title),
          actions: actions,
          leading: leading,
          bottom: bottom,
          backgroundColor: bg.withOpacity(isDark ? 0.55 : 0.62),
          surfaceTintColor: Colors.transparent,
          scrolledUnderElevation: 0,
          elevation: 0,
          shape: Border(
            bottom: BorderSide(
              color: isDark
                  ? Colors.white.withOpacity(0.06)
                  : Colors.white.withOpacity(0.55),
            ),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: Rodar o teste e ver passar**

Run: `flutter test test/glass_app_bar_test.dart`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add lib/core/ui/glass_app_bar.dart test/glass_app_bar_test.dart
git commit -m "feat(app): GlassAppBar — appbar de vidro reutilizavel"
```

---

### Task 3: Adotar GlassAppBar nas telas internas

**Files:**
- Modify: `lib/features/conexao/conexao_screen.dart`
- Modify: `lib/features/rede/rede_screen.dart`
- Modify: `lib/features/fidelidade/fidelidade_screen.dart`
- Modify: `lib/features/indicacao/indicacao_screen.dart`
- Modify: `lib/features/notificacoes/notificacoes_screen.dart`
- Modify: `lib/features/faq/faq_screen.dart`

Receita mecânica, **uma tela por vez** (commit por tela ou um commit pro lote, a critério — mas analyze entre cada uma):

- [ ] **Step 1: Pra cada tela da lista, aplicar a receita**

1. Localizar o `Scaffold` principal da tela (grep `appBar:`).
2. Trocar `appBar: AppBar(title: Text('X'), ...)` por `appBar: GlassAppBar(title: 'X', ...)` — preservando `actions`/`leading` existentes. Se o `AppBar` da tela usar parâmetro que `GlassAppBar` não tem (ex: `flexibleSpace`, `toolbarHeight` custom), **pular a tela** e anotar no commit.
3. Adicionar `extendBodyBehindAppBar: true` no mesmo `Scaffold`.
4. Compensar o topo do body: se o body for scrollable (`ListView`/`SingleChildScrollView`/`CustomScrollView`), garantir padding superior `MediaQuery.paddingOf(context).top + kToolbarHeight + BrandTokens.spaceMd`. Se a tela usa `SafeArea` envolvendo o body, trocar por `SafeArea(top: false, ...)` + o padding acima (senão o SafeArea anula o efeito de rolar por baixo).
5. Adicionar o import: `import '../../core/ui/glass_app_bar.dart';` (ajustar o nível de `../` conforme a pasta).

- [ ] **Step 2: Verificar a cada tela**

Run: `flutter analyze`
Expected: sem warning/error novos.

Smoke visual (se desejar): `flutter run` e navegar pelas 6 telas, conferir que o conteúdo rola por baixo do appbar com blur e que nada ficou escondido atrás dele no topo.

- [ ] **Step 3: Commit**

```bash
git add lib/features
git commit -m "polish(app): GlassAppBar nas telas internas (conexao, rede, fidelidade, indicacao, notificacoes, faq)"
```

---

### Task 4: Componentes padronizados de estado (ErrorCard, EmptyState, AsyncBuilder)

**Files:**
- Create: `lib/core/ui/async_states.dart`
- Test: `test/async_states_test.dart`

Hoje cada tela tem seu estilo de loading/erro/vazio. Este task cria o trio padrão; a adoção começa nas telas da Task 3 que tiverem padrão simples (sem perder skeletons especializados tipo `_HeroSkeleton` da home — esses ficam).

- [ ] **Step 1: Escrever os testes (falhando)**

`test/async_states_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cliente_mobile/core/ui/async_states.dart';

void main() {
  Widget wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

  testWidgets('ErrorCard mostra mensagem e chama onRetry', (tester) async {
    var retried = false;
    await tester.pumpWidget(wrap(
      ErrorCard(
        message: 'Não conseguimos carregar agora.',
        onRetry: () => retried = true,
      ),
    ));
    expect(find.text('Não conseguimos carregar agora.'), findsOneWidget);
    await tester.tap(find.text('Tentar de novo'));
    expect(retried, isTrue);
  });

  testWidgets('EmptyState mostra icone, titulo e subtitulo', (tester) async {
    await tester.pumpWidget(wrap(
      const EmptyState(
        icon: Icons.inbox_rounded,
        title: 'Nada por aqui',
        subtitle: 'Quando algo chegar, aparece nesta tela.',
      ),
    ));
    expect(find.byIcon(Icons.inbox_rounded), findsOneWidget);
    expect(find.text('Nada por aqui'), findsOneWidget);
    expect(find.text('Quando algo chegar, aparece nesta tela.'), findsOneWidget);
  });

  testWidgets('AsyncBuilder renderiza data/loading/error', (tester) async {
    // data
    await tester.pumpWidget(wrap(
      AsyncBuilder<String>(
        value: const AsyncValue.data('oi'),
        builder: (data) => Text(data),
      ),
    ));
    expect(find.text('oi'), findsOneWidget);

    // loading (default = spinner centralizado)
    await tester.pumpWidget(wrap(
      AsyncBuilder<String>(
        value: const AsyncValue.loading(),
        builder: (data) => Text(data),
      ),
    ));
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    // error (default = ErrorCard)
    await tester.pumpWidget(wrap(
      AsyncBuilder<String>(
        value: AsyncValue<String>.error('boom', StackTrace.empty),
        builder: (data) => Text(data),
      ),
    ));
    expect(find.byType(ErrorCard), findsOneWidget);
  });
}
```

(Gotcha CI: `depend_on_referenced_packages` — `flutter_riverpod` já é dependency direta do pubspec, ok importar no teste.)

- [ ] **Step 2: Rodar e ver falhar**

Run: `flutter test test/async_states_test.dart`
Expected: FAIL (arquivo não existe).

- [ ] **Step 3: Implementar**

`lib/core/ui/async_states.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../branding/brand_tokens.dart';

/// Card de erro padrão do app: mensagem amigável + retry.
class ErrorCard extends StatelessWidget {
  const ErrorCard({
    super.key,
    this.message = 'Não conseguimos carregar agora.',
    this.onRetry,
  });

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        color: BrandTokens.danger.withOpacity(isDark ? 0.12 : 0.06),
        borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
        border: Border.all(color: BrandTokens.danger.withOpacity(0.25)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.wifi_off_rounded,
              color: BrandTokens.danger, size: 32),
          const SizedBox(height: BrandTokens.spaceSm),
          Text(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          if (onRetry != null) ...[
            const SizedBox(height: BrandTokens.spaceMd),
            TextButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded, size: 18),
              label: const Text('Tentar de novo'),
            ),
          ],
        ],
      ),
    );
  }
}

/// Estado vazio padrão: ícone grande suave + título + subtítulo.
class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.subtitle,
  });

  final IconData icon;
  final String title;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    final secondary = Theme.of(context).brightness == Brightness.dark
        ? BrandTokens.textSecondaryDark
        : BrandTokens.textSecondary;
    return Padding(
      padding: const EdgeInsets.all(BrandTokens.spaceXl),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              color: BrandTokens.primary.withOpacity(0.10),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: BrandTokens.primary, size: 34),
          ),
          const SizedBox(height: BrandTokens.spaceMd),
          Text(
            title,
            textAlign: TextAlign.center,
            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
          ),
          if (subtitle != null) ...[
            const SizedBox(height: BrandTokens.spaceXs),
            Text(
              subtitle!,
              textAlign: TextAlign.center,
              style: TextStyle(color: secondary, fontSize: 13, height: 1.4),
            ),
          ],
        ],
      ),
    );
  }
}

/// Wrapper padrão pra AsyncValue: data → builder, loading → spinner
/// (ou skeleton custom), error → ErrorCard (ou custom).
class AsyncBuilder<T> extends StatelessWidget {
  const AsyncBuilder({
    super.key,
    required this.value,
    required this.builder,
    this.loading,
    this.error,
    this.onRetry,
  });

  final AsyncValue<T> value;
  final Widget Function(T data) builder;
  final Widget? loading;
  final Widget? error;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return value.when(
      data: builder,
      loading: () =>
          loading ??
          const Padding(
            padding: EdgeInsets.all(BrandTokens.spaceXl),
            child: Center(child: CircularProgressIndicator()),
          ),
      error: (_, __) => error ?? ErrorCard(onRetry: onRetry),
    );
  }
}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `flutter test test/async_states_test.dart`
Expected: PASS (3 testes).

- [ ] **Step 5: Adotar nas telas simples**

Em `notificacoes_screen.dart`, `faq_screen.dart` e `conexao_screen.dart`: localizar os `.when(loading: ..., error: ...)` que renderizam spinner/erro genérico inline e trocar pelo `AsyncBuilder` (passando `onRetry: () => ref.invalidate(<provider da tela>)`). Onde houver lista vazia com placeholder inline, trocar por `EmptyState`. **Não mexer** em skeletons especializados (home) nem nos fluxos com cache fallback (`_CachedHeroOrError`).

- [ ] **Step 6: Verificar e commit**

Run: `flutter analyze && flutter test`
Expected: limpo / PASS.

```bash
git add lib/core/ui/async_states.dart test/async_states_test.dart lib/features
git commit -m "feat(app): ErrorCard/EmptyState/AsyncBuilder padronizados + adocao inicial"
```

---

### Task 5: Tokens novos + migração de cores hex hardcoded

**Files:**
- Modify: `lib/core/branding/brand_tokens.dart`
- Modify: arquivos listados no Step 2

**Critério (importante):** `Colors.white`/`white70` sobre gradientes/vidro são INTENCIONAIS — não migrar. O alvo são literais `Color(0xFF...)` espalhados nas features. Hexes que JÁ são tokens (`0xFF14B8B0`=primary, `0xFF0B1F3A`=primaryDark, `0xFF051329`=backgroundDark, `0xFFF4F8FA`=background, `0xFFE8A33D`=warning, `0xFFE0455A`=danger) → substituir pela referência. Hexes novos recorrentes → virar token.

- [ ] **Step 1: Adicionar tokens novos em `brand_tokens.dart`**

Após o bloco "Cores categóricas" (linha ~38), adicionar:

```dart
  // Tons derivados de status (usados em gradientes/ênfase)
  static const Color successBright = Color(0xFF22E0A1); // verde conexão ok
  static const Color dangerDeep = Color(0xFFB12B40); // fim de gradiente vencida
  static const Color dangerStrong = Color(0xFFCC2233); // barra breaking de manutenção
  static const Color warningBright = Color(0xFFF59E0B);
  static const Color neutralGrey = Color(0xFF6B7280); // status desconhecido
  static const Color neutralGreyDark = Color(0xFF374151);

  // Cores de marca de terceiros (canais de contato)
  static const Color brandWhatsapp = Color(0xFF25D366);
  static const Color brandWhatsappDark = Color(0xFF128C7E);
  static const Color brandInstagram = Color(0xFFE1306C);
  static const Color brandFacebook = Color(0xFF1877F2);

  // Tons de destaque pontuais
  static const Color accentOrange = Color(0xFFFF8E53); // gradiente quick card
  static const Color accentPink = Color(0xFFFF6B9D); // banner aniversariante

  // Fallback de gradiente de promoção (quando admin não define cores)
  static const Color promoFallbackFrom = Color(0xFF8B5CF6);
  static const Color promoFallbackTo = Color(0xFF5B6CFF);
```

- [ ] **Step 2: Migrar os arquivos (mapa exato)**

Substituições por arquivo (manter `withOpacity` que existir; adicionar import de `brand_tokens.dart` se faltar):

| Arquivo | De | Para |
|---|---|---|
| `lib/features/home/widgets/connection_status_pill.dart:64` | `Color(0xFF22E0A1)` | `BrandTokens.successBright` |
| `lib/features/home/widgets/promo_carousel.dart:133-134` | `Color(0xFF8B5CF6)` / `Color(0xFF5B6CFF)` | `BrandTokens.promoFallbackFrom` / `BrandTokens.promoFallbackTo` |
| `lib/features/home/widgets/manutencao_breaking_bar.dart:93,100,122,129` | `Color(0xFFE0455A)` / `Color(0xFFCC2233)` | `BrandTokens.danger` / `BrandTokens.dangerStrong` |
| `lib/features/home/widgets/quick_cards_row.dart:55,62` | `Color(0xFFE8A33D)` / `Color(0xFFFF8E53)` | `BrandTokens.warning` / `BrandTokens.accentOrange` |
| `lib/features/home/widgets/quick_cards_row.dart:206,213` | `Color(0xFF25D366)` / `Color(0xFF128C7E)` | `BrandTokens.brandWhatsapp` / `BrandTokens.brandWhatsappDark` |
| `lib/features/home/widgets/hero_card.dart:267` | `Color(0xFFE8A33D)` | `BrandTokens.warning` |
| `lib/features/home/widgets/aniversariante_banner.dart:86,93` | `Color(0xFFFF6B9D)` / `Color(0xFFFF8E53)` | `BrandTokens.accentPink` / `BrandTokens.accentOrange` |
| `lib/features/faturas/widgets/comprovante_card.dart:37-39,252` | consts locais `_gold`/`_navy`/`_teal` | apontar pra `BrandTokens.warning` / `BrandTokens.primaryDark` / `BrandTokens.primary` (manter os aliases locais, só trocar o valor: `static const Color _gold = BrandTokens.warning;`) |
| `lib/features/faturas/widgets/comprovante_card.dart:62,149,263-265,294,299,412,431,515` | hexes que são tokens (`0xFF051329`, `0xFF0B1F3A`, `0xFF14B8B0`, `0xFFF4F8FA`, `0xFFE8A33D`) | tokens correspondentes (`backgroundDark`, `primaryDark`, `primary`, `background`, `warning`). `Color(0xFF134A6F)` é tom intermediário do gradiente do share-card — deixar inline com comentário `// tom intermediário do gradiente, exclusivo deste card`. |
| `lib/features/faturas/faturas_screen.dart:179,253` | `Color(0xFFB12B40)` / `Color(0xFFE8A33D)` | `BrandTokens.dangerDeep` / `BrandTokens.warning` |
| `lib/features/contatos/contatos_screen.dart:59,67,69` | WhatsApp/Instagram/Facebook | `BrandTokens.brandWhatsapp` / `brandInstagram` / `brandFacebook` |
| `lib/features/conexao/conexao_screen.dart:93,104,117,130` | gradientes de status | `[BrandTokens.primary, BrandTokens.successBright]`, `[BrandTokens.warning, BrandTokens.warningBright]`, `[BrandTokens.danger, BrandTokens.dangerDeep]`, `[BrandTokens.neutralGrey, BrandTokens.neutralGreyDark]` |
| `lib/features/indicacao/widgets/indicacao_share_card.dart:39-40` | `0xFF0B1F3A` / `0xFF14B8B0` | `BrandTokens.primaryDark` / `BrandTokens.primary` |

**Atenção:** gradientes `const LinearGradient(colors: [Color(...), ...])` continuam const com tokens (`BrandTokens.*` são `static const`). Se o analyzer reclamar de const-ness em algum caso com `withOpacity`, remover o `const` do nível necessário.

Depois do mapa acima, rodar `grep -rEn "Color\(0x" lib --include="*.dart" | grep -v brand_tokens` e tratar sobras óbvias com o mesmo critério (token existente → referenciar; cor única de contexto → deixar com comentário).

- [ ] **Step 3: Verificar**

Run: `flutter analyze && flutter test`
Expected: limpo / PASS.

- [ ] **Step 4: Commit**

```bash
git add lib
git commit -m "polish(app): cores hex hardcoded migradas pra BrandTokens (+ tokens novos)"
```

---

### Task 6: Microinteração — auto-scroll do carrossel de promos

**Files:**
- Modify: `lib/features/home/widgets/promo_carousel.dart`

Auto-avança a cada 6s com easing suave; pausa quando o usuário toca/arrasta e retoma 10s depois da última interação. Wrap-around pro início.

- [ ] **Step 1: Adicionar timer de auto-scroll no `_PromoCarouselState`**

Adicionar campos e métodos (depois de `_viewTimer`):

```dart
  Timer? _autoTimer;
  Timer? _resumeTimer;

  void _startAuto() {
    _autoTimer?.cancel();
    if (widget.items.length < 2) return;
    _autoTimer = Timer.periodic(const Duration(seconds: 6), (_) {
      if (!mounted || !_ctrl.hasClients) return;
      final next = (_idx + 1) % widget.items.length;
      _ctrl.animateToPage(
        next,
        duration: const Duration(milliseconds: 480),
        curve: const Cubic(0.32, 0.72, 0, 1),
      );
    });
  }

  // Usuário tocou: pausa o auto-scroll e retoma após 10s de inatividade.
  void _pauseAuto() {
    _autoTimer?.cancel();
    _resumeTimer?.cancel();
    _resumeTimer = Timer(const Duration(seconds: 10), () {
      if (mounted) _startAuto();
    });
  }
```

No `initState`, depois de `_scheduleView(0);` adicionar `_startAuto();`.
No `dispose`, antes de `_viewTimer?.cancel();` adicionar:

```dart
    _autoTimer?.cancel();
    _resumeTimer?.cancel();
```

- [ ] **Step 2: Pausar na interação do usuário**

Envolver o `PageView.builder` num `Listener`:

```dart
          child: Listener(
            onPointerDown: (_) => _pauseAuto(),
            child: PageView.builder(
              // ... (inalterado)
            ),
          ),
```

- [ ] **Step 3: Verificar e commit**

Run: `flutter analyze`
Expected: limpo.

```bash
git add lib/features/home/widgets/promo_carousel.dart
git commit -m "polish(app): auto-scroll suave no carrossel de promos (pausa na interacao)"
```

---

### Task 7: Microinteração — PressableScale nos cards

**Files:**
- Create: `lib/core/ui/pressable_scale.dart`
- Test: `test/pressable_scale_test.dart`
- Modify: `lib/features/home/widgets/promo_carousel.dart` (no `_PromoCard`)
- Modify: `lib/features/home/widgets/quick_cards_row.dart`

Feedback tátil visual: card encolhe levemente (0.97) enquanto pressionado — sensação iOS.

- [ ] **Step 1: Teste (falhando)**

`test/pressable_scale_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cliente_mobile/core/ui/pressable_scale.dart';

void main() {
  testWidgets('PressableScale chama onTap e renderiza child', (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: PressableScale(
          onTap: () => tapped = true,
          child: const Text('card'),
        ),
      ),
    );
    expect(find.text('card'), findsOneWidget);
    await tester.tap(find.text('card'));
    await tester.pumpAndSettle();
    expect(tapped, isTrue);
  });
}
```

(Mesmo gotcha do nome do package da Task 2.)

- [ ] **Step 2: Rodar e ver falhar**

Run: `flutter test test/pressable_scale_test.dart`
Expected: FAIL.

- [ ] **Step 3: Implementar**

`lib/core/ui/pressable_scale.dart`:

```dart
import 'package:flutter/material.dart';

import '../branding/brand_tokens.dart';

/// Encolhe o child levemente enquanto pressionado (feel iOS).
/// Não substitui InkWell — envolve por fora (escala o card inteiro,
/// incluindo sombra/gradiente).
class PressableScale extends StatefulWidget {
  const PressableScale({
    super.key,
    required this.child,
    this.onTap,
    this.scale = 0.97,
  });

  final Widget child;
  final VoidCallback? onTap;
  final double scale;

  @override
  State<PressableScale> createState() => _PressableScaleState();
}

class _PressableScaleState extends State<PressableScale> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapDown: (_) => setState(() => _pressed = true),
      onTapCancel: () => setState(() => _pressed = false),
      onTapUp: (_) => setState(() => _pressed = false),
      onTap: widget.onTap,
      child: AnimatedScale(
        duration: BrandTokens.motionFast,
        curve: Curves.easeOut,
        scale: _pressed ? widget.scale : 1.0,
        child: widget.child,
      ),
    );
  }
}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `flutter test test/pressable_scale_test.dart`
Expected: PASS.

- [ ] **Step 5: Adotar no `_PromoCard` e nos quick cards**

Em `promo_carousel.dart`, no `_PromoCard.build`, trocar o `Material`+`InkWell` externo por:

```dart
    return PressableScale(
      onTap: () => onTap(item),
      child: Container(
        // ... (Container com gradient inalterado, remover Material/InkWell)
      ),
    );
```

(import: `import '../../../core/ui/pressable_scale.dart';`)

Em `quick_cards_row.dart`: localizar os cards clicáveis (grep `InkWell` ou `GestureDetector`) e envolver cada card no `PressableScale` mantendo o handler existente — se o card usa `InkWell` com ripple desejado, manter o InkWell DENTRO do PressableScale e passar `onTap` apenas no InkWell (PressableScale sem `onTap` só faz a escala? **Não** — sem onTap o GestureDetector ainda consome o tap. Nesse caso, mover o handler pro PressableScale e remover o InkWell, igual ao _PromoCard).

- [ ] **Step 6: Verificar e commit**

Run: `flutter analyze && flutter test`
Expected: limpo / PASS.

```bash
git add lib/core/ui/pressable_scale.dart test/pressable_scale_test.dart lib/features/home/widgets
git commit -m "polish(app): pressed-scale nos cards (promo + quick actions)"
```

---

### Task 8: Transições de página customizadas (GoRouter)

**Files:**
- Modify: `lib/router.dart`

Fade + slide horizontal sutil com a curva iOS já usada na navbar. Aplica nas rotas internas (push de telas); rotas de auth/splash/shell ficam como estão.

- [ ] **Step 1: Adicionar helper de página no `router.dart`**

Antes de `final routerProvider`, adicionar:

```dart
/// Transição padrão das telas internas: fade + slide sutil (curva iOS).
CustomTransitionPage<void> _glassPage(GoRouterState state, Widget child) {
  return CustomTransitionPage<void>(
    key: state.pageKey,
    child: child,
    transitionDuration: const Duration(milliseconds: 320),
    reverseTransitionDuration: const Duration(milliseconds: 280),
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      final curved = CurvedAnimation(
        parent: animation,
        curve: const Cubic(0.32, 0.72, 0, 1),
      );
      return FadeTransition(
        opacity: curved,
        child: SlideTransition(
          position: Tween<Offset>(
            begin: const Offset(0.04, 0),
            end: Offset.zero,
          ).animate(curved),
          child: child,
        ),
      );
    },
  );
}
```

- [ ] **Step 2: Converter as rotas internas de `builder` pra `pageBuilder`**

Pra estas rotas — `/perfil/editar`, `/perfil/mudar-senha`, `/suporte/novo`, `/indicacao`, `/conexao`, `/rede`, `/notificacoes`, `/notificacoes/preferencias`, `/contatos`, `/fidelidade`, `/faq`, `/faq/:artigoId`, `/legal/termos`, `/legal/privacidade` — trocar o padrão:

```dart
      // antes
      GoRoute(path: '/conexao', builder: (_, __) => const ConexaoScreen()),
      // depois
      GoRoute(
        path: '/conexao',
        pageBuilder: (_, state) => _glassPage(state, const ConexaoScreen()),
      ),
```

Nas rotas que usam `state.extra`/`pathParameters` (ex: `/perfil/editar`, `/faq/:artigoId`), manter a extração igual, só movendo pra dentro do `pageBuilder`:

```dart
      GoRoute(
        path: '/perfil/editar',
        pageBuilder: (_, state) {
          final extra = state.extra as Map<String, String>?;
          return _glassPage(
            state,
            EditarPerfilScreen(
              campo: extra?['campo'] ?? 'telefone',
              valor: extra?['valor'] ?? '',
            ),
          );
        },
      ),
```

**Não converter:** `/splash`, `/login`, `/forgot/reset`, `/onboarding/*`, `/home` e as rotas-redirect (`/faturas`, `/suporte`).

- [ ] **Step 3: Verificar e commit**

Run: `flutter analyze && flutter test`
Expected: limpo / PASS.

```bash
git add lib/router.dart
git commit -m "polish(app): transicao fade+slide custom nas telas internas"
```

---

### Task 9: Verificação final

- [ ] **Step 1: Suíte completa**

Run: `flutter analyze && flutter test`
Expected: analyze sem warning/error (info ok); todos os testes PASS.

- [ ] **Step 2: Smoke visual (manual, com Robert ou emulador)**

Checklist: navbar com blur visível ao rolar a home (light e dark); appbars de vidro nas 6 telas internas sem conteúdo escondido no topo; carrossel auto-avança e pausa ao tocar; cards encolhem ao pressionar; transições suaves ao abrir telas internas; dark mode íntegro nas telas migradas de cor.

- [ ] **Step 3: Aguardar OK do Robert pra push**

Push = CI (flutter analyze no gate). Não pushar sem confirmação.
