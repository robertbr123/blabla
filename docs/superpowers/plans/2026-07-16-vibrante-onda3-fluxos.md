# Identidade Vibrante — Onda 3: telas empurradas (Rede, Fidelidade, Notificações, Novo chamado)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aplicar a identidade "Vibrante de marca" nas telas empurradas de alto tráfego, substituindo o padrão `GlassAppBar + extendBodyBehindAppBar` por um scaffold compartilhado capa+folha.

**Architecture:** Task 1 cria `CapaPageScaffold` (capa compacta com botão voltar + título + ações + slot opcional abaixo do título, e folha com o body). Tasks 2–5 migram cada tela pra ele, removendo compensações de altura do header antigo (paddings top calculados com `kToolbarHeight`). ZERO mudança de lógica.

**Tech Stack:** Flutter; building blocks existentes `CapaBackground`/`FolhaContainer` (lib/core/ui/capa_folha.dart), tokens `BrandTokens`.

## Global Constraints

- Diretório: `apps/cliente-mobile`. Commits direto na main, um por task. NÃO dar push.
- `lib/features/conexao/conexao_screen.dart` está FORA desta onda (WIP não commitado do Robert) — não tocar.
- ZERO mudança de lógica/providers/navegação; só casca + remoção de compensações do header antigo (`MediaQuery.paddingOf(context).top + kToolbarHeight`-style paddings viram o padding natural da folha).
- Título das telas empurradas: mesmo estilo das tabs — `TextStyle(color: BrandTokens.capaInk, fontSize: 24, fontWeight: FontWeight.w900, letterSpacing: -0.6)`.
- Listas/scroll dentro da folha; bottom padding das listas dessas telas: manter o atual se ≥ 24 (não há navbar flutuante em telas empurradas — ela é só do shell) e garantir `MediaQuery.paddingOf(context).bottom` incluído onde a tela já incluía.
- Gate por task: `flutter test` verde + `flutter analyze lib test` ZERO errors/warnings, sem issues novas (~158 infos pré-existentes; nunca `flutter analyze` puro). NUNCA `git add -A`.
- Cada task de tela: ler o arquivo INTEIRO antes de editar.

---

### Task 1: CapaPageScaffold compartilhado

**Files:**
- Create: `lib/core/ui/capa_page_scaffold.dart`
- Test: `test/capa_page_scaffold_test.dart`

**Interfaces:**
- Consumes: `CapaBackground`, `FolhaContainer`, tokens.
- Produces: `class CapaPageScaffold extends StatelessWidget` com construtor `CapaPageScaffold({super.key, required String title, List<Widget> actions = const [], Widget? capaBottom, required Widget child, EdgeInsetsGeometry? folhaPadding})`. Tasks 2–5 consomem.

- [ ] **Step 1: Teste (falhando primeiro).** Criar `test/capa_page_scaffold_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cliente_mobile/core/ui/capa_page_scaffold.dart';

void main() {
  testWidgets('renderiza titulo, child e botao voltar quando pode pop',
      (t) async {
    await t.pumpWidget(MaterialApp(
      home: const Placeholder(),
    ));
    // Empurra uma rota pra Navigator.canPop ser true.
    final nav = t.state<NavigatorState>(find.byType(Navigator));
    nav.push(MaterialPageRoute(
      builder: (_) => const CapaPageScaffold(
        title: 'Minha tela',
        child: Text('conteudo'),
      ),
    ));
    await t.pumpAndSettle();
    expect(find.text('Minha tela'), findsOneWidget);
    expect(find.text('conteudo'), findsOneWidget);
    expect(find.byIcon(Icons.arrow_back_rounded), findsOneWidget);
  });

  testWidgets('sem botao voltar quando nao pode pop', (t) async {
    await t.pumpWidget(const MaterialApp(
      home: CapaPageScaffold(title: 'Raiz', child: Text('x')),
    ));
    expect(find.byIcon(Icons.arrow_back_rounded), findsNothing);
  });
}
```

Run: `flutter test test/capa_page_scaffold_test.dart` → FAIL (arquivo não existe).

- [ ] **Step 2: Implementar** `lib/core/ui/capa_page_scaffold.dart`:

```dart
import 'package:flutter/material.dart';

import '../branding/brand_tokens.dart';
import 'capa_folha.dart';

/// Scaffold padrão das telas empurradas na identidade vibrante:
/// capa ciano compacta (voltar + título + ações + slot opcional) e
/// folha clara com o conteúdo. Substitui o GlassAppBar.
class CapaPageScaffold extends StatelessWidget {
  const CapaPageScaffold({
    super.key,
    required this.title,
    this.actions = const [],
    this.capaBottom,
    required this.child,
    this.folhaPadding,
  });

  final String title;
  final List<Widget> actions;

  /// Slot opcional na capa abaixo da linha do título (ex: TabBar, chips).
  final Widget? capaBottom;

  /// Conteúdo da folha (geralmente um scrollável).
  final Widget child;

  /// Padding da folha; default zero (o conteúdo cuida do próprio padding).
  final EdgeInsetsGeometry? folhaPadding;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final canPop = Navigator.of(context).canPop();
    return Scaffold(
      backgroundColor:
          isDark ? BrandTokens.backgroundDark : BrandTokens.background,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          CapaBackground(
            padding: EdgeInsets.fromLTRB(
              BrandTokens.spaceMd,
              MediaQuery.paddingOf(context).top + BrandTokens.spaceSm,
              BrandTokens.spaceMd,
              BrandTokens.spaceLg + BrandTokens.radiusFolha,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    if (canPop)
                      IconButton(
                        icon: const Icon(
                          Icons.arrow_back_rounded,
                          color: BrandTokens.capaInk,
                        ),
                        onPressed: () => Navigator.of(context).pop(),
                      )
                    else
                      const SizedBox(width: BrandTokens.spaceSm),
                    Expanded(
                      child: Text(
                        title,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: BrandTokens.capaInk,
                          fontSize: 24,
                          fontWeight: FontWeight.w900,
                          letterSpacing: -0.6,
                        ),
                      ),
                    ),
                    ...actions,
                  ],
                ),
                if (capaBottom != null) ...[
                  const SizedBox(height: BrandTokens.spaceSm),
                  capaBottom!,
                ],
              ],
            ),
          ),
          Expanded(
            child: FolhaContainer(
              overlap: BrandTokens.radiusFolha,
              padding: folhaPadding ?? EdgeInsets.zero,
              child: child,
            ),
          ),
        ],
      ),
    );
  }
}
```

Run: `flutter test test/capa_page_scaffold_test.dart` → PASS.

- [ ] **Step 3: Gates + commit.** `flutter test` (17 verdes) + `flutter analyze lib test` (0 err/warn). `git add lib/core/ui/capa_page_scaffold.dart test/capa_page_scaffold_test.dart` + `git commit -m "feat(cliente): CapaPageScaffold — scaffold capa+folha pras telas empurradas"`.

---

### Task 2: Minha Rede com CapaPageScaffold

**Files:**
- Modify: `lib/features/rede/rede_screen.dart`

- [ ] **Step 1:** Ler a tela inteira (656 linhas). Hoje: `extendBodyBehindAppBar + GlassAppBar(title: 'Minha Rede WiFi')`; o body compensa a altura do header.
- [ ] **Step 2:** Migrar pra `CapaPageScaffold(title: 'Minha Rede WiFi', child: <body atual>)`. Remover GlassAppBar/extendBodyBehindAppBar e compensações de topo (padding top do scrollável vira `BrandTokens.spaceLg`). Ações do header (se houver) viram `actions` com ícones em `capaInk`. RefreshIndicator/estados/ações (trocar senha WiFi etc.) intactos.
- [ ] **Step 3:** Gates + commit `feat(cliente): minha rede com capa vibrante`.

---

### Task 3: Fidelidade com CapaPageScaffold

**Files:**
- Modify: `lib/features/fidelidade/fidelidade_screen.dart`

- [ ] **Step 1:** Ler a tela inteira (698 linhas). Hoje: `GlassAppBar(title: 'Programa de fidelidade')`. Diálogo de resgate e lógica de pontos intactos.
- [ ] **Step 2:** Migrar pra `CapaPageScaffold(title: 'Fidelidade', ...)` — título encurtado pra caber no estilo display; se a tela tiver um hero de pontos no topo do body, avaliar movê-lo pro `capaBottom` SÓ se for uma mudança de casca trivial (senão fica na folha).
- [ ] **Step 3:** Gates + commit `feat(cliente): fidelidade com capa vibrante`.

---

### Task 4: Notificações + Preferências com CapaPageScaffold

**Files:**
- Modify: `lib/features/notificacoes/notificacoes_screen.dart`
- Modify: `lib/features/notificacoes/notif_prefs_screen.dart`

- [ ] **Step 1:** Ler as duas (319 + 213 linhas). Notificações tem actions no GlassAppBar (ex: marcar todas lidas / engrenagem de prefs) — preservar como `actions` em capaInk.
- [ ] **Step 2:** Migrar ambas pro `CapaPageScaffold` (`title: 'Notificações'` / `'Preferências'`), removendo compensações. Lógica (marcar lida, toggles de prefs) intacta.
- [ ] **Step 3:** Gates + commit único `feat(cliente): notificacoes e preferencias com capa vibrante`.

---

### Task 5: Novo chamado com CapaPageScaffold

**Files:**
- Modify: `lib/features/suporte/novo_chamado_screen.dart`

- [ ] **Step 1:** Ler a tela inteira (441 linhas). É um formulário/fluxo de abertura de chamado — teclado importa: garantir que o scroll do formulário continua funcionando com teclado aberto (o `Expanded(FolhaContainer(child: scrollável))` do CapaPageScaffold + `resizeToAvoidBottomInset` default cuidam disso).
- [ ] **Step 2:** Migrar pra `CapaPageScaffold(title: 'Novo chamado', ...)`. Campos de texto podem continuar com o estilo atual (restyle de inputs internos NÃO é escopo desta onda).
- [ ] **Step 3:** Gates + commit `feat(cliente): novo chamado com capa vibrante`.

---

### Task 6: Verificação da onda

- [ ] **Step 1:** `flutter test` verde + `flutter analyze lib test` (0 err/warn) + `flutter build apk --debug` ok.
- [ ] **Step 2:** Review whole-branch da onda (base = commit anterior à Task 1) com atenção a: uso consistente do CapaPageScaffold, compensações de header órfãs, teclado no novo chamado, GlassAppBar ainda usado em telas fora da onda (ok — sai nas próximas).
- [ ] **Step 3:** Checklist manual (Robert): navegar Home → Minha rede / sino → Notificações → Preferências / Fidelidade / Suporte → Novo chamado; dark mode; voltar sempre visível.
