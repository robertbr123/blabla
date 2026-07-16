# Redesign Login + Home (cliente-mobile) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aplicar a identidade "Vibrante de marca" (capa ciano + folha clara) nas telas de login, reset de senha e home do app cliente, com lembrar-CPF e desbloqueio biométrico, preservando todos os cards/fluxos existentes.

**Architecture:** Novos tokens aditivos em `BrandTokens` + dois building blocks reutilizáveis (`CapaBackground` com onda decorativa e `FolhaContainer` com cantos arredondados). Login/reset viram capa+folha; a home ganha um header `HomeCapa` que absorve o conteúdo do `HeroCard` e do `RedeDestaqueCard`, e um `FaturaCard` novo abre a folha. Biometria reusa a infra existente (`BiometricService`, flag `biometricEnabled` no secure storage) como gate no splash + botão no login.

**Tech Stack:** Flutter 3.27+, Riverpod 2, go_router, flutter_secure_storage, local_auth (todos já no pubspec — nenhuma dependência nova).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-15-redesign-login-home-cliente-design.md`.
- Diretório de trabalho: `apps/cliente-mobile` (todos os paths abaixo são relativos a ele).
- Tokens existentes em `BrandTokens` NÃO mudam de valor — só adições (outras telas não podem ser afetadas).
- Nenhum card/fluxo da home é removido: multi-contrato (switcher), streak badge, NPS auto-popup, pull-to-refresh, cache last-known, breaking bar — tudo preservado.
- Nenhuma mudança de backend/API.
- Modo escuro: capa ciano igual nos dois temas; folha usa `backgroundDark`/`surfaceDark` no dark.
- Gate de qualidade por task: `flutter analyze` limpo (regra de CI do repo).
- Commits direto na `main`, um por task. **NÃO dar push** — Robert dá push manualmente (push = deploy).
- Sem dev stack local além do Flutter: validação em aparelho é do Robert, após push.
- Copy exata dos textos: título do login `onde\nvocê\nestiver.` (3 linhas), tagline `Ondeline — internet que acompanha você.`, saudações `Bom dia,` / `Boa tarde,` / `Boa noite,`.

---

### Task 1: Tokens da nova identidade em BrandTokens

**Files:**
- Modify: `lib/core/branding/brand_tokens.dart` (adições no fim da classe)

**Interfaces:**
- Produces: `BrandTokens.capaInk` (Color), `BrandTokens.capaDeep` (Color), `BrandTokens.gradientCapa` (LinearGradient), `BrandTokens.radiusFolha` (double = 28), `BrandTokens.displayTitle` e `BrandTokens.displayGreeting` (TextStyle). Tasks 2–8 consomem.

- [ ] **Step 1: Adicionar tokens**

Em `lib/core/branding/brand_tokens.dart`, dentro da classe `BrandTokens`, após o bloco de gradients existente, adicionar:

```dart
  // ── Identidade "Vibrante de marca" (redesign login+home 2026-07) ──

  /// Tinta escura pra texto sobre a capa ciano.
  static const Color capaInk = Color(0xFF04222B);

  /// Tom profundo que fecha o gradiente da capa.
  static const Color capaDeep = Color(0xFF0C6E75);

  /// Gradiente da capa (topo do login e da home).
  static const LinearGradient gradientCapa = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [primary, accentDark, capaDeep],
    stops: [0.0, 0.6, 1.0],
  );

  /// Raio dos cantos superiores da "folha" sobreposta à capa.
  static const double radiusFolha = 28;

  /// Título display gigante (login).
  static const TextStyle displayTitle = TextStyle(
    color: capaInk,
    fontSize: 40,
    fontWeight: FontWeight.w900,
    letterSpacing: -1.2,
    height: 1.0,
  );

  /// Saudação da capa da home.
  static const TextStyle displayGreeting = TextStyle(
    color: capaInk,
    fontSize: 26,
    fontWeight: FontWeight.w900,
    letterSpacing: -0.8,
    height: 1.1,
  );
```

- [ ] **Step 2: Verificar análise estática**

Run: `flutter analyze`
Expected: `No issues found!`

- [ ] **Step 3: Commit**

```bash
git add lib/core/branding/brand_tokens.dart
git commit -m "feat(cliente): tokens da identidade vibrante (capa ciano + folha)"
```

---

### Task 2: Building blocks CapaBackground e FolhaContainer

**Files:**
- Create: `lib/core/ui/capa_folha.dart`
- Test: `test/capa_folha_test.dart`

**Interfaces:**
- Consumes: tokens da Task 1.
- Produces:
  - `class CapaBackground extends StatelessWidget` — `CapaBackground({super.key, required Widget child, EdgeInsetsGeometry? padding})`: container com `gradientCapa` + onda decorativa desenhada por `_WavePainter`, filho por cima.
  - `class FolhaContainer extends StatelessWidget` — `FolhaContainer({super.key, required Widget child, EdgeInsetsGeometry padding = const EdgeInsets.all(BrandTokens.spaceMd), double overlap = 0})`: folha com cantos superiores `radiusFolha`, cor `background`/`backgroundDark` conforme tema; `overlap > 0` aplica `Transform.translate` de `-overlap` no eixo Y pra sobrepor a capa.

- [ ] **Step 1: Escrever teste de widget (falhando)**

Criar `test/capa_folha_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cliente_mobile/core/branding/brand_tokens.dart';
import 'package:cliente_mobile/core/ui/capa_folha.dart';

void main() {
  testWidgets('CapaBackground renderiza filho sobre o gradiente', (t) async {
    await t.pumpWidget(const MaterialApp(
      home: CapaBackground(child: Text('capa')),
    ));
    expect(find.text('capa'), findsOneWidget);
  });

  testWidgets('FolhaContainer usa background claro no tema light', (t) async {
    await t.pumpWidget(MaterialApp(
      theme: ThemeData(brightness: Brightness.light),
      home: const FolhaContainer(child: Text('folha')),
    ));
    final box = t.widget<Container>(
      find.ancestor(of: find.text('folha'), matching: find.byType(Container)).first,
    );
    final deco = box.decoration as BoxDecoration;
    expect(deco.color, BrandTokens.background);
    expect(find.text('folha'), findsOneWidget);
  });

  testWidgets('FolhaContainer usa backgroundDark no tema dark', (t) async {
    await t.pumpWidget(MaterialApp(
      theme: ThemeData(brightness: Brightness.dark),
      home: const FolhaContainer(child: Text('folha')),
    ));
    final box = t.widget<Container>(
      find.ancestor(of: find.text('folha'), matching: find.byType(Container)).first,
    );
    final deco = box.decoration as BoxDecoration;
    expect(deco.color, BrandTokens.backgroundDark);
  });
}
```

- [ ] **Step 2: Rodar teste e ver falhar**

Run: `flutter test test/capa_folha_test.dart`
Expected: FAIL — `Error: Couldn't resolve the package 'cliente_mobile/core/ui/capa_folha.dart'` (arquivo não existe).

- [ ] **Step 3: Implementar capa_folha.dart**

Criar `lib/core/ui/capa_folha.dart`:

```dart
import 'package:flutter/material.dart';

import '../branding/brand_tokens.dart';

/// Fundo "capa" da identidade vibrante: gradiente ciano + onda decorativa.
/// Usado no topo do login e da home.
class CapaBackground extends StatelessWidget {
  const CapaBackground({super.key, required this.child, this.padding});

  final Widget child;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(gradient: BrandTokens.gradientCapa),
      child: CustomPaint(
        painter: _WavePainter(),
        child: Padding(
          padding: padding ?? EdgeInsets.zero,
          child: child,
        ),
      ),
    );
  }
}

/// Duas ondas suaves em stroke branco de baixa opacidade, ancoradas no
/// terço inferior da capa — referência ao "onde" da Ondeline.
class _WavePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint1 = Paint()
      ..color = Colors.white.withValues(alpha: 0.16)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    final paint2 = Paint()
      ..color = Colors.white.withValues(alpha: 0.10)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;

    final y = size.height * 0.72;
    final w = size.width;

    Path onda(double baseY, double amp) {
      final p = Path()..moveTo(0, baseY);
      p.quadraticBezierTo(w * 0.17, baseY - amp, w * 0.33, baseY);
      p.quadraticBezierTo(w * 0.50, baseY + amp, w * 0.67, baseY);
      p.quadraticBezierTo(w * 0.83, baseY - amp, w, baseY);
      return p;
    }

    canvas.drawPath(onda(y, 14), paint1);
    canvas.drawPath(onda(y + 16, 12), paint2);
  }

  @override
  bool shouldRepaint(covariant _WavePainter oldDelegate) => false;
}

/// "Folha" clara com cantos superiores arredondados que sobrepõe a capa.
/// No dark mode vira folha azul-marinho (backgroundDark).
class FolhaContainer extends StatelessWidget {
  const FolhaContainer({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(BrandTokens.spaceMd),
    this.overlap = 0,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  /// Quantos pixels a folha sobe por cima da capa (margin-top negativa).
  final double overlap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final folha = Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: isDark ? BrandTokens.backgroundDark : BrandTokens.background,
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(BrandTokens.radiusFolha),
        ),
      ),
      padding: padding,
      child: child,
    );
    if (overlap == 0) return folha;
    return Transform.translate(offset: Offset(0, -overlap), child: folha);
  }
}
```

- [ ] **Step 4: Rodar teste e ver passar**

Run: `flutter test test/capa_folha_test.dart`
Expected: `All tests passed!`

- [ ] **Step 5: Analyze + commit**

Run: `flutter analyze` → `No issues found!`

```bash
git add lib/core/ui/capa_folha.dart test/capa_folha_test.dart
git commit -m "feat(cliente): building blocks CapaBackground + FolhaContainer"
```

---

### Task 3: Lembrar CPF do último acesso

**Files:**
- Modify: `lib/core/auth/auth_storage.dart`
- Modify: `lib/core/auth/auth_repository.dart` (método `login`)
- Modify: `lib/features/auth/login_screen.dart` (`initState`)

**Interfaces:**
- Produces: `Future<String?> readLastCpf()` e `Future<void> writeLastCpf(String cpfDigits)` em `auth_storage.dart` (CPF completo, 11 dígitos, no secure storage). Task 4/6 consomem.

- [ ] **Step 1: Adicionar chave e funções no auth_storage**

Em `lib/core/auth/auth_storage.dart`, junto às outras consts `_k*`:

```dart
const _kCpfFull = 'cliente_cpf_full';
```

E junto às funções de leitura/escrita:

```dart
/// CPF completo do último login bem-sucedido — pré-preenche a tela de login.
/// Fica no secure storage (mesma proteção do token) e NÃO é limpo no logout,
/// pra facilitar o próximo acesso do mesmo cliente.
Future<String?> readLastCpf() => _storage.read(key: _kCpfFull);
Future<void> writeLastCpf(String cpfDigits) =>
    _storage.write(key: _kCpfFull, value: cpfDigits);
```

Atenção: NÃO adicionar `_kCpfFull` ao `clearAuth()` (decisão do spec: lembrar CPF sobrevive ao logout).

- [ ] **Step 2: Gravar no login bem-sucedido**

Em `lib/core/auth/auth_repository.dart`, dentro de `login(...)`, logo após a linha `final cpfDigits = cpf.replaceAll(RegExp(r'\D'), '');`, adicionar:

```dart
    await writeLastCpf(cpfDigits);
```

- [ ] **Step 3: Pré-preencher no login screen**

Em `lib/features/auth/login_screen.dart`, no `_LoginScreenState.initState()`, substituir o corpo atual:

```dart
  @override
  void initState() {
    super.initState();
    final cpf = widget.initialCpf;
    if (cpf != null && cpf.length == 11) {
      _cpfCtrl.text = formatCpf(cpf);
      return;
    }
    // Sem CPF vindo do onboarding: tenta o último CPF logado (best-effort;
    // storage pode falhar em testes/simulador sem keychain — ignora).
    readLastCpf().then((saved) {
      if (!mounted || saved == null || saved.length != 11) return;
      if (_cpfCtrl.text.isNotEmpty) return;
      setState(() => _cpfCtrl.text = formatCpf(saved));
    }).catchError((_) {});
  }
```

E adicionar o import no topo:

```dart
import '../../core/auth/auth_storage.dart';
```

- [ ] **Step 4: Analyze + commit**

Run: `flutter analyze` → `No issues found!`

```bash
git add lib/core/auth/auth_storage.dart lib/core/auth/auth_repository.dart lib/features/auth/login_screen.dart
git commit -m "feat(cliente): lembrar CPF do ultimo acesso no login"
```

---

### Task 4: Redesign da tela de login (capa + folha)

**Files:**
- Create: `lib/core/ui/sheet_text_field.dart`
- Modify: `lib/features/auth/login_screen.dart` (só o método `build` e imports — estado/handlers `_login`, `_forgot`, `_toast` ficam intactos)

**Interfaces:**
- Consumes: `CapaBackground`, `FolhaContainer` (Task 2); tokens (Task 1).
- Produces: layout novo; `class SheetTextField extends StatelessWidget` em `lib/core/ui/sheet_text_field.dart` — mesmo construtor do snippet abaixo — que a Task 5 também importa.

- [ ] **Step 1: Reescrever o build**

Substituir os imports de UI que saem de uso e o método `build` inteiro de `_LoginScreenState`:

Imports — remover `animated_gradient_background.dart` e `glass_card.dart`; adicionar `capa_folha.dart`:

```dart
import '../../core/ui/capa_folha.dart';
```

Novo `build`:

```dart
  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      backgroundColor: isDark ? BrandTokens.backgroundDark : BrandTokens.background,
      resizeToAvoidBottomInset: true,
      body: GestureDetector(
        onTap: () => FocusScope.of(context).unfocus(),
        behavior: HitTestBehavior.translucent,
        child: CustomScrollView(
          slivers: [
            SliverFillRemaining(
              hasScrollBody: false,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // ── Capa ciano com tipografia display ──
                  Expanded(
                    child: CapaBackground(
                      padding: EdgeInsets.only(
                        left: BrandTokens.spaceLg,
                        right: BrandTokens.spaceLg,
                        top: MediaQuery.paddingOf(context).top + BrandTokens.spaceXl,
                        bottom: BrandTokens.spaceXl + BrandTokens.radiusFolha,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: const [
                          Text('onde\nvocê\nestiver.', style: BrandTokens.displayTitle),
                          SizedBox(height: BrandTokens.spaceSm),
                          Text(
                            'Ondeline — internet que acompanha você.',
                            style: TextStyle(
                              color: BrandTokens.capaInk,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  // ── Folha com o formulário ──
                  FolhaContainer(
                    overlap: BrandTokens.radiusFolha,
                    padding: EdgeInsets.fromLTRB(
                      BrandTokens.spaceLg,
                      BrandTokens.spaceLg,
                      BrandTokens.spaceLg,
                      MediaQuery.paddingOf(context).bottom + BrandTokens.spaceLg,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _SheetTextField(
                          controller: _cpfCtrl,
                          label: 'CPF',
                          keyboardType: TextInputType.number,
                          inputFormatters: [
                            FilteringTextInputFormatter.digitsOnly,
                            LengthLimitingTextInputFormatter(11),
                            CpfFormatter(),
                          ],
                          prefixIcon: Icons.badge_outlined,
                        ),
                        const SizedBox(height: BrandTokens.spaceMd),
                        _SheetTextField(
                          controller: _pwdCtrl,
                          label: 'Senha',
                          obscureText: _hide,
                          prefixIcon: Icons.lock_outline,
                          suffix: IconButton(
                            icon: Icon(
                              _hide
                                  ? Icons.visibility_outlined
                                  : Icons.visibility_off_outlined,
                              size: 20,
                            ),
                            onPressed: () => setState(() => _hide = !_hide),
                          ),
                        ),
                        const SizedBox(height: BrandTokens.spaceSm),
                        Align(
                          alignment: Alignment.centerRight,
                          child: TextButton(
                            onPressed: _loading ? null : _forgot,
                            style: TextButton.styleFrom(
                              foregroundColor: BrandTokens.primary,
                              padding: EdgeInsets.zero,
                              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            ),
                            child: const Text(
                              'Esqueci minha senha',
                              style: TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ),
                        ),
                        const SizedBox(height: BrandTokens.spaceMd),
                        FilledButton(
                          onPressed: _loading ? null : _login,
                          style: FilledButton.styleFrom(
                            backgroundColor: BrandTokens.primary,
                            foregroundColor: Colors.white,
                            minimumSize: const Size.fromHeight(52),
                            shape: RoundedRectangleBorder(
                              borderRadius:
                                  BorderRadius.circular(BrandTokens.radiusMd),
                            ),
                            textStyle: const TextStyle(
                              fontWeight: FontWeight.w800,
                              fontSize: 16,
                            ),
                          ),
                          child: _loading
                              ? const SizedBox(
                                  width: 22,
                                  height: 22,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2.5,
                                    color: Colors.white,
                                  ),
                                )
                              : const Text('Entrar'),
                        ),
                        const SizedBox(height: BrandTokens.spaceSm),
                        TextButton(
                          onPressed: _loading
                              ? null
                              : () => context.go('/onboarding/cpf'),
                          style: TextButton.styleFrom(
                            minimumSize: const Size.fromHeight(44),
                            foregroundColor: isDark
                                ? BrandTokens.textPrimaryDark
                                : BrandTokens.textPrimary,
                          ),
                          child: const Text.rich(
                            TextSpan(
                              text: 'Novo aqui? ',
                              children: [
                                TextSpan(
                                  text: 'Criar conta',
                                  style: TextStyle(
                                    fontWeight: FontWeight.w800,
                                    color: BrandTokens.primary,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
```

- [ ] **Step 2: Criar lib/core/ui/sheet_text_field.dart**

O `build` acima usa `_SheetTextField` — trocar as ocorrências por `SheetTextField` e importar `../../core/ui/sheet_text_field.dart`. Conteúdo do arquivo novo (imports: `package:flutter/material.dart`, `package:flutter/services.dart`, `../branding/brand_tokens.dart`):

```dart
/// Campo de texto da folha clara — surface branca/marinho, borda que acende
/// em ciano no foco. Substitui o GlassTextField nas telas de auth novas.
class SheetTextField extends StatelessWidget {
  const SheetTextField({
    super.key,
    required this.controller,
    required this.label,
    this.keyboardType,
    this.inputFormatters,
    this.obscureText = false,
    this.prefixIcon,
    this.suffix,
  });

  final TextEditingController controller;
  final String label;
  final TextInputType? keyboardType;
  final List<TextInputFormatter>? inputFormatters;
  final bool obscureText;
  final IconData? prefixIcon;
  final Widget? suffix;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      inputFormatters: inputFormatters,
      obscureText: obscureText,
      style: TextStyle(
        fontWeight: FontWeight.w600,
        color: isDark ? BrandTokens.textPrimaryDark : BrandTokens.textPrimary,
      ),
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: prefixIcon == null ? null : Icon(prefixIcon, size: 20),
        suffixIcon: suffix,
        filled: true,
        fillColor: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          borderSide: BorderSide(
            color: isDark ? Colors.white12 : BrandTokens.divider,
          ),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          borderSide: BorderSide(
            color: isDark ? Colors.white12 : BrandTokens.divider,
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          borderSide: const BorderSide(color: BrandTokens.primary, width: 1.5),
        ),
      ),
    );
  }
}
```

Import necessário no topo do arquivo (se ainda não existir): `package:flutter/services.dart` (já existe — usado pelos formatters).

- [ ] **Step 3: Analyze + commit**

Run: `flutter analyze` → `No issues found!` (atenção: se `glass_card.dart` ficou sem uso no arquivo, o import precisa ter sido removido).

```bash
git add lib/core/ui/sheet_text_field.dart lib/features/auth/login_screen.dart
git commit -m "feat(cliente): redesign da tela de login — capa vibrante + folha"
```

---

### Task 5: Reset de senha com a mesma roupagem

**Files:**
- Modify: `lib/features/auth/forgot_reset_screen.dart`

**Interfaces:**
- Consumes: `CapaBackground`, `FolhaContainer` (Task 2). Lógica de OTP/reset intacta.

- [ ] **Step 1: Ler o arquivo e trocar só a casca visual**

Ler `lib/features/auth/forgot_reset_screen.dart` (140 linhas). Manter TODOS os controllers/handlers. Substituir o `Scaffold`/fundo atual (`AnimatedGradientBackground` + `GlassCard`/`GlassTextField`/`GlassPrimaryButton`, ou o que estiver lá) pela mesma estrutura da Task 4:

- Capa compacta no topo (não precisa do título gigante): `CapaBackground` com padding `top: MediaQuery.paddingOf(context).top + BrandTokens.spaceLg`, contendo um botão voltar (`IconButton` com `Icons.arrow_back_rounded`, cor `BrandTokens.capaInk`) e título `Redefinir senha` em `TextStyle(color: BrandTokens.capaInk, fontSize: 24, fontWeight: FontWeight.w900, letterSpacing: -0.6)` + subtítulo `Digite o código que enviamos no seu WhatsApp.` (fontSize 13, capaInk com 70% de opacidade via `BrandTokens.capaInk.withValues(alpha: 0.7)`).
- Folha (`FolhaContainer` com `overlap: BrandTokens.radiusFolha`) contendo os campos existentes (código + nova senha) restilizados com o `SheetTextField` compartilhado (`import '../../core/ui/sheet_text_field.dart'`, criado na Task 4).
- Botão de confirmar vira o mesmo `FilledButton` ciano da Task 4 (label existente mantida).
- A capa aqui NÃO usa `Expanded` (conteúdo rola): estrutura = `Column` com capa de altura natural + `Expanded(child: SingleChildScrollView(child: FolhaContainer(...)))`.

- [ ] **Step 2: Analyze + commit**

Run: `flutter analyze` → `No issues found!`

```bash
git add lib/features/auth/forgot_reset_screen.dart
git commit -m "feat(cliente): reset de senha com capa vibrante + folha"
```

---

### Task 6: Biometria — gate no splash + botão no login + opt-in pós-login

**Files:**
- Modify: `lib/features/splash/splash_screen.dart` (método `_decide`)
- Modify: `lib/features/auth/login_screen.dart`

**Interfaces:**
- Consumes: `biometricServiceProvider` (`isAvailable()`, `authenticate(String reason)`) de `lib/core/auth/biometric_service.dart`; `readBiometricEnabled()`, `writeBiometricEnabled(bool)`, `readAccessToken()` de `auth_storage.dart` — tudo já existe.
- Produces: fluxo — splash com token + biometria ativa exige Face ID/digital; falha/cancelamento cai no login com botão "Entrar com biometria" que repete o desbloqueio (token continua no storage até logout).

- [ ] **Step 1: Gate no splash**

Em `lib/features/splash/splash_screen.dart`, substituir `_decide()`:

```dart
  Future<void> _decide() async {
    await Future.delayed(const Duration(milliseconds: 1100));
    if (!mounted) return;
    final hasToken =
        await ref.read(hasTokenProvider.future).catchError((_) => false);
    if (!mounted) return;
    if (!hasToken) {
      context.go('/onboarding/cpf');
      return;
    }
    // Token válido: se o cliente ativou biometria, exige desbloqueio.
    final bioEnabled = await readBiometricEnabled().catchError((_) => false);
    if (!mounted) return;
    if (!bioEnabled) {
      context.go('/home');
      return;
    }
    final bio = ref.read(biometricServiceProvider);
    final ok = await bio.isAvailable() &&
        await bio.authenticate('Desbloqueie o app Ondeline');
    if (!mounted) return;
    // Falhou/cancelou: cai no login (senha ou nova tentativa de biometria).
    context.go(ok ? '/home' : '/login');
  }
```

Imports a adicionar:

```dart
import '../../core/auth/auth_storage.dart';
import '../../core/auth/biometric_service.dart';
```

- [ ] **Step 2: Botão de biometria no login**

Em `lib/features/auth/login_screen.dart`:

No `_LoginScreenState`, adicionar campo e carregar no `initState` (após o bloco do CPF):

```dart
  bool _bioAvailable = false;
```

```dart
    // Botão "Entrar com biometria": só quando há sessão guardada + flag ativa
    // + hardware disponível.
    Future.wait([
      readAccessToken().catchError((_) => null),
      readBiometricEnabled().catchError((_) => false),
      ref.read(biometricServiceProvider).isAvailable(),
    ]).then((r) {
      final hasToken = r[0] != null;
      final enabled = r[1] == true;
      final available = r[2] == true;
      if (!mounted) return;
      setState(() => _bioAvailable = hasToken && enabled && available);
    });
```

Handler novo no state:

```dart
  Future<void> _loginBiometria() async {
    final ok = await ref
        .read(biometricServiceProvider)
        .authenticate('Entre com sua digital ou Face ID');
    if (!mounted) return;
    if (!ok) return;
    await Haptics.success();
    ref.read(authRefreshProvider).bump();
    if (!mounted) return;
    context.go('/home');
  }
```

No `build`, logo após o `FilledButton` de Entrar (antes do `SizedBox` + botão Criar conta), inserir:

```dart
                        if (_bioAvailable) ...[
                          const SizedBox(height: BrandTokens.spaceSm),
                          OutlinedButton.icon(
                            onPressed: _loading ? null : _loginBiometria,
                            style: OutlinedButton.styleFrom(
                              minimumSize: const Size.fromHeight(52),
                              foregroundColor: BrandTokens.primary,
                              side: const BorderSide(
                                  color: BrandTokens.primary, width: 1.2),
                              shape: RoundedRectangleBorder(
                                borderRadius:
                                    BorderRadius.circular(BrandTokens.radiusMd),
                              ),
                              textStyle: const TextStyle(
                                  fontWeight: FontWeight.w800, fontSize: 15),
                            ),
                            icon: const Icon(Icons.fingerprint_rounded),
                            label: const Text('Entrar com biometria'),
                          ),
                        ],
```

Import novo: `import '../../core/auth/biometric_service.dart';`

- [ ] **Step 3: Opt-in pós-login com senha**

Ainda em `login_screen.dart`, no `_login()`, trocar o case `AuthOk()`:

```dart
      case AuthOk():
        await Haptics.success();
        ref.read(authRefreshProvider).bump();
        if (!mounted) return;
        await _maybeOfferBiometria();
        if (!mounted) return;
        context.go('/home');
```

E adicionar o método:

```dart
  /// Oferece ativar biometria uma vez após login com senha (opt-in).
  Future<void> _maybeOfferBiometria() async {
    final enabled = await readBiometricEnabled().catchError((_) => false);
    if (enabled) return;
    final available =
        await ref.read(biometricServiceProvider).isAvailable();
    if (!available || !mounted) return;
    final aceitar = await showModalBottomSheet<bool>(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(BrandTokens.radiusFolha),
        ),
      ),
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(
          BrandTokens.spaceLg,
          BrandTokens.spaceLg,
          BrandTokens.spaceLg,
          MediaQuery.paddingOf(ctx).bottom + BrandTokens.spaceLg,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Icon(Icons.fingerprint_rounded,
                size: 48, color: BrandTokens.primary),
            const SizedBox(height: BrandTokens.spaceMd),
            Text(
              'Entrar mais rápido?',
              textAlign: TextAlign.center,
              style: Theme.of(ctx).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.5,
                  ),
            ),
            const SizedBox(height: BrandTokens.spaceXs),
            Text(
              'Use sua digital ou Face ID pra desbloquear o app sem digitar a senha.',
              textAlign: TextAlign.center,
              style: Theme.of(ctx).textTheme.bodyMedium,
            ),
            const SizedBox(height: BrandTokens.spaceLg),
            FilledButton(
              onPressed: () => Navigator.of(ctx).pop(true),
              style: FilledButton.styleFrom(
                backgroundColor: BrandTokens.primary,
                minimumSize: const Size.fromHeight(48),
              ),
              child: const Text('Ativar biometria'),
            ),
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('Agora não'),
            ),
          ],
        ),
      ),
    );
    if (aceitar == true) {
      await writeBiometricEnabled(true);
    }
  }
```

- [ ] **Step 4: Analyze + commit**

Run: `flutter analyze` → `No issues found!`

```bash
git add lib/features/splash/splash_screen.dart lib/features/auth/login_screen.dart
git commit -m "feat(cliente): biometria no splash e login + opt-in pos-senha"
```

---

### Task 7: HomeCapa — header vibrante com status de rede integrado

**Files:**
- Create: `lib/features/home/widgets/home_capa.dart`
- Modify: `lib/core/ui/formatters.dart` (helper `saudacao`)
- Test: `test/saudacao_test.dart`

**Interfaces:**
- Consumes: `CapaBackground` (Task 2); `MeDto` (nome, planoNome, statusConexao, contratos, temMultiContrato); `redeAparelhosProvider` → `RedeAparelhosDto(encontrada, aparelhos, saude)`; `showContratoSelector(context, ref, me)` de `contrato_switcher.dart`; `NotifBell` de `../notificacoes/widgets/notif_bell.dart`; `ConnectionStatusPill` de `connection_status_pill.dart`.
- Produces: `class HomeCapa extends ConsumerWidget` — `HomeCapa({super.key, required MeDto me})`. `String saudacao(DateTime now)` em formatters.dart. Task 8 monta a home com `HomeCapa`.

- [ ] **Step 1: Teste do helper de saudação (falhando)**

Criar `test/saudacao_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';

import 'package:cliente_mobile/core/ui/formatters.dart';

void main() {
  test('saudacao por faixa de horario', () {
    expect(saudacao(DateTime(2026, 1, 1, 5)), 'Bom dia,');
    expect(saudacao(DateTime(2026, 1, 1, 11, 59)), 'Bom dia,');
    expect(saudacao(DateTime(2026, 1, 1, 12)), 'Boa tarde,');
    expect(saudacao(DateTime(2026, 1, 1, 17, 59)), 'Boa tarde,');
    expect(saudacao(DateTime(2026, 1, 1, 18)), 'Boa noite,');
    expect(saudacao(DateTime(2026, 1, 1, 4, 59)), 'Boa noite,');
  });
}
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `flutter test test/saudacao_test.dart`
Expected: FAIL — `saudacao` não definida.

- [ ] **Step 3: Implementar saudacao em formatters.dart**

Adicionar ao fim de `lib/core/ui/formatters.dart`:

```dart
/// Saudação por faixa de horário (5h–11h59 dia, 12h–17h59 tarde, resto noite).
String saudacao(DateTime now) {
  final h = now.hour;
  if (h >= 5 && h < 12) return 'Bom dia,';
  if (h >= 12 && h < 18) return 'Boa tarde,';
  return 'Boa noite,';
}
```

Run: `flutter test test/saudacao_test.dart` → `All tests passed!`

- [ ] **Step 4: Implementar HomeCapa**

Criar `lib/features/home/widgets/home_capa.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api/dto.dart';
import '../../../core/api/rede_repository.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../../core/contrato/contrato_atual_provider.dart';
import '../../../core/ui/capa_folha.dart';
import '../../../core/ui/formatters.dart';
import '../../../core/ui/pressable_scale.dart';
import '../../notificacoes/widgets/notif_bell.dart';
import 'connection_status_pill.dart';
import 'contrato_switcher.dart';

/// Capa ciano da home: saudação + sino + bloco de status integrado
/// (conexão, plano, aparelhos conectados, atalho Minha rede) + linha de
/// endereço/troca de contrato. Absorve o conteúdo do antigo topo do
/// HeroCard e do RedeDestaqueCard.
class HomeCapa extends ConsumerWidget {
  const HomeCapa({super.key, required this.me});
  final MeDto me;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final contratoAtual = me.contratos.isEmpty ? null : _contratoAtual(ref);
    return CapaBackground(
      padding: EdgeInsets.fromLTRB(
        BrandTokens.spaceLg,
        MediaQuery.paddingOf(context).top + BrandTokens.spaceMd,
        BrandTokens.spaceLg,
        BrandTokens.spaceLg + BrandTokens.radiusFolha,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      saudacao(DateTime.now()),
                      style: TextStyle(
                        color: BrandTokens.capaInk.withValues(alpha: 0.65),
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    Text(
                      '${_primeiroNome(me.nome)} 👋',
                      style: BrandTokens.displayGreeting,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              const NotifBell(),
            ],
          ),
          const SizedBox(height: BrandTokens.spaceMd),
          _StatusBlock(me: me),
          if (contratoAtual != null &&
              contratoAtual.enderecoResumido.isNotEmpty)
            _ContratoLinha(
              contrato: contratoAtual,
              podeTrocar: me.temMultiContrato,
              onTrocar: () => showContratoSelector(context, ref, me),
            ),
        ],
      ),
    );
  }

  ContratoResumoDto _contratoAtual(WidgetRef ref) {
    final id = ref.watch(contratoAtualProvider);
    return me.contratos.firstWhere(
      (c) => c.id == id,
      orElse: () => me.contratos.first,
    );
  }

  String _primeiroNome(String full) {
    final t = full.trim();
    if (t.isEmpty) return 'Cliente';
    final p = t.split(RegExp(r'\s+')).first;
    if (p.isEmpty) return 'Cliente';
    return p[0].toUpperCase() + p.substring(1).toLowerCase();
  }
}

/// Bloco translúcido com status da conexão + plano + linha de rede.
/// Degradê gracioso: sem dados de rede (ONU não mapeada ou erro), mostra
/// só status + plano — o acesso à rede continua nas ações rápidas.
class _StatusBlock extends ConsumerWidget {
  const _StatusBlock({required this.me});
  final MeDto me;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final redeAsync = ref.watch(redeAparelhosProvider);
    final rede = redeAsync.maybeWhen(
      data: (d) => d.encontrada ? d : null,
      orElse: () => null,
    );
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceMd),
      decoration: BoxDecoration(
        color: BrandTokens.capaInk.withValues(alpha: 0.22),
        borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const ConnectionStatusPill(),
              const SizedBox(width: BrandTokens.spaceSm),
              Expanded(
                child: Text(
                  me.planoNome ?? 'Sem plano vinculado',
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          if (rede != null) ...[
            const SizedBox(height: BrandTokens.spaceSm),
            Row(
              children: [
                Expanded(
                  child: Text(
                    '📱 ${rede.aparelhos.length} '
                    '${rede.aparelhos.length == 1 ? "aparelho" : "aparelhos"}'
                    ' · sinal ${_saudeLabel(rede.saude)}',
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.85),
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                PressableScale(
                  onTap: () => context.push('/rede'),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: BrandTokens.spaceSm + 2,
                      vertical: 5,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.22),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Text(
                      'Minha rede →',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  String _saudeLabel(String saude) => switch (saude) {
        'excelente' => 'Ótimo',
        'boa' => 'Bom',
        'fraca' => 'Fraco',
        _ => 'Ativo',
      };
}

/// Linha de endereço do contrato na capa; clicável quando multi-contrato.
class _ContratoLinha extends StatelessWidget {
  const _ContratoLinha({
    required this.contrato,
    required this.podeTrocar,
    required this.onTrocar,
  });
  final ContratoResumoDto contrato;
  final bool podeTrocar;
  final VoidCallback onTrocar;

  @override
  Widget build(BuildContext context) {
    final linha = Padding(
      padding: const EdgeInsets.only(top: BrandTokens.spaceSm),
      child: Row(
        children: [
          Icon(Icons.location_on_outlined,
              size: 14, color: BrandTokens.capaInk.withValues(alpha: 0.7)),
          const SizedBox(width: 4),
          Expanded(
            child: Text(
              contrato.enderecoResumido,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: BrandTokens.capaInk.withValues(alpha: 0.7),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          if (podeTrocar)
            Icon(Icons.swap_horiz_rounded,
                size: 16, color: BrandTokens.capaInk.withValues(alpha: 0.7)),
        ],
      ),
    );
    if (!podeTrocar) return linha;
    return GestureDetector(onTap: onTrocar, child: linha);
  }
}
```

- [ ] **Step 5: Analyze + commit**

Run: `flutter analyze` → `No issues found!`
Run: `flutter test` → todos passam (novos + existentes).

```bash
git add lib/features/home/widgets/home_capa.dart lib/core/ui/formatters.dart test/saudacao_test.dart
git commit -m "feat(cliente): HomeCapa — header vibrante com status de rede integrado"
```

---

### Task 8: Home nova — FaturaCard + reorder + folha

**Files:**
- Create: `lib/features/home/widgets/fatura_card.dart`
- Modify: `lib/features/home/home_screen.dart`
- Modify: `lib/features/home/widgets/hero_card.dart` (extrair `StreakBadge` público OU mover pro novo arquivo — ver Step 2)
- Delete: uso do `RedeDestaqueCard` na home (arquivo `rede_destaque_card.dart` é deletado junto com `test/rede_destaque_card_test.dart`)

**Interfaces:**
- Consumes: `HomeCapa` (Task 7), `FolhaContainer` (Task 2), `faturasAbertasProvider` → `List<FaturaDto>` (`valor` double, `vencimento` String, `status`), `mainShellTabProvider` (tab 1 = faturas).
- Produces: home final. `class FaturaCard extends ConsumerWidget` (auto-hide sem fatura aberta); `class StreakBadge` público reutilizado na folha.

- [ ] **Step 1: Implementar FaturaCard**

Criar `lib/features/home/widgets/fatura_card.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/api/faturas_repository.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../../core/ui/pressable_scale.dart';
import '../../shell/main_shell.dart';

/// Primeiro card da folha: fatura em aberto mais urgente com CTA de pagar.
/// Auto-hide quando não há fatura aberta (estado "em dia" fica implícito
/// no status da capa) ou em erro/loading.
class FaturaCard extends ConsumerWidget {
  const FaturaCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final faturasAsync = ref.watch(faturasAbertasProvider);
    final fatura = faturasAsync.maybeWhen(
      data: (l) => l.isEmpty ? null : l.first,
      orElse: () => null,
    );
    if (fatura == null) return const SizedBox.shrink();

    final isDark = Theme.of(context).brightness == Brightness.dark;
    final venc = DateTime.tryParse(fatura.vencimento);
    final vencLabel =
        venc == null ? fatura.vencimento : DateFormat('dd/MM').format(venc);
    final valor = NumberFormat.currency(locale: 'pt_BR', symbol: r'R$')
        .format(fatura.valor);

    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceMd),
      child: PressableScale(
        onTap: () => ref.read(mainShellTabProvider.notifier).state = 1,
        child: Container(
          padding: const EdgeInsets.all(BrandTokens.spaceMd),
          decoration: BoxDecoration(
            color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
            borderRadius: BorderRadius.circular(BrandTokens.radiusMd + 2),
            border: Border.all(
              color: isDark ? Colors.white12 : BrandTokens.divider,
            ),
            boxShadow: BrandTokens.elevation2,
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'FATURA EM ABERTO',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.5,
                        color: isDark
                            ? BrandTokens.textSecondaryDark
                            : BrandTokens.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      valor,
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.5,
                      ),
                    ),
                    Text(
                      'vence em $vencLabel',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: isDark
                            ? BrandTokens.textSecondaryDark
                            : BrandTokens.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: BrandTokens.spaceMd,
                  vertical: 10,
                ),
                decoration: BoxDecoration(
                  color: BrandTokens.primary,
                  borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
                ),
                child: const Text(
                  'Pagar Pix',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Realocar o StreakBadge**

Em `lib/features/home/widgets/hero_card.dart`: renomear a classe privada `_StreakBadge` pra `StreakBadge` (pública) e movê-la (com os imports que ela usa, ex. `streak_repository.dart`) pra um arquivo novo `lib/features/home/widgets/streak_badge.dart`. O `hero_card.dart` continua existindo (não é mais usado na home, mas o `_CachedHeroOrError` sai também — ver Step 3; se após o Step 3 `hero_card.dart` ficar sem NENHUM uso no app, deletar o arquivo e conferir imports órfãos com `flutter analyze`).

- [ ] **Step 3: Reescrever a estrutura do home_screen.dart**

Em `lib/features/home/home_screen.dart`, substituir o `build` mantendo TODOS os comportamentos (`ref.listen` do NPS, `_onRefresh`, `_maybePromptNps`, `_persistMe`):

```dart
  @override
  Widget build(BuildContext context) {
    final meAsync = ref.watch(meProvider);
    final avisosAsync = ref.watch(avisosProvider);
    final promosAsync = ref.watch(promocoesProvider);

    ref.listen<AsyncValue<List<OsDto>>>(osListProvider, (_, next) {
      next.whenData(_maybePromptNps);
    });

    return Scaffold(
      body: RefreshIndicator(
        onRefresh: _onRefresh,
        edgeOffset: MediaQuery.paddingOf(context).top,
        child: ListView(
          physics: const BouncingScrollPhysics(
            parent: AlwaysScrollableScrollPhysics(),
          ),
          padding: const EdgeInsets.only(bottom: 120),
          children: [
            // ── Capa (edge-to-edge, cuida do status bar padding) ──
            meAsync.when(
              data: (me) {
                _persistMe(me);
                return HomeCapa(me: me);
              },
              loading: () => const _CapaSkeleton(),
              error: (_, __) => _CachedCapaOrError(ref),
            ),
            // ── Folha ──
            FolhaContainer(
              overlap: BrandTokens.radiusFolha,
              padding: const EdgeInsets.fromLTRB(
                BrandTokens.spaceLg,
                BrandTokens.spaceLg,
                BrandTokens.spaceLg,
                0,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const ManutencaoBreakingBar(),
                  meAsync.maybeWhen(
                    data: (me) => AniversarianteBanner(me: me),
                    orElse: () => const SizedBox.shrink(),
                  ),
                  const FaturaCard(),
                  const StreakBadge(),
                  const _SectionLabel(label: 'Ações rapidas'),
                  const SizedBox(height: BrandTokens.spaceSm),
                  QuickActions(
                    actions: [
                      QuickAction(
                        icon: Icons.wifi_rounded,
                        label: 'Minha rede',
                        color: BrandTokens.primary,
                        onTap: () => context.push('/rede'),
                      ),
                      QuickAction(
                        icon: Icons.receipt_long_outlined,
                        label: '2a via',
                        color: BrandTokens.catBilling,
                        onTap: () =>
                            ref.read(mainShellTabProvider.notifier).state = 1,
                      ),
                      QuickAction(
                        icon: Icons.support_agent_outlined,
                        label: 'Falar conosco',
                        color: BrandTokens.catSupport,
                        onTap: () =>
                            ref.read(mainShellTabProvider.notifier).state = 2,
                      ),
                      QuickAction(
                        icon: Icons.wifi_off_outlined,
                        label: 'Sem internet',
                        color: BrandTokens.catConnection,
                        onTap: () => context.push('/suporte/novo'),
                      ),
                      QuickAction(
                        icon: Icons.swap_horiz_rounded,
                        label: 'Mudar plano',
                        color: BrandTokens.catPlan,
                        onTap: () => context.push('/suporte/novo'),
                      ),
                    ],
                  ),
                  const SizedBox(height: BrandTokens.spaceLg),
                  const QuickCardsRow(),
                  const CardDoDia(),
                  ...promosAsync.when(
                    data: (promos) {
                      if (promos.isEmpty) return const <Widget>[];
                      return [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const _SectionLabel(label: 'Pra você'),
                            if (promos.length > 1)
                              TextButton(
                                onPressed: () => context.push('/promocoes'),
                                child: const Text('Ver todas →'),
                              ),
                          ],
                        ),
                        const SizedBox(height: BrandTokens.spaceSm),
                        PromoCarousel(items: promos),
                        const SizedBox(height: BrandTokens.spaceLg),
                      ];
                    },
                    loading: () => const <Widget>[],
                    error: (_, __) => const <Widget>[],
                  ),
                  avisosAsync.when(
                    data: (a) => AvisosList(avisos: a),
                    loading: () => const SizedBox.shrink(),
                    error: (_, __) => const SizedBox.shrink(),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
```

Mudanças estruturais a observar:
- `SafeArea` sai do topo (a capa cobre o status bar); o `NotifBell` avulso sai (vive na capa agora).
- `ManutencaoBreakingBar` entra no topo da folha (continua "acima de tudo" visualmente por ser o primeiro item; auto-hide mantido).
- Imports: remover `rede_destaque_card.dart` e `hero_card.dart`; adicionar `home_capa.dart`, `fatura_card.dart`, `streak_badge.dart`, `../../core/ui/capa_folha.dart`.
- Substituir `_HeroSkeleton` por `_CapaSkeleton` (mesmo shape, altura 220, cantos zero — é a capa) e `_CachedHeroOrError` por `_CachedCapaOrError` (mesma lógica de cache, mas renderiza `HomeCapa(me: me)` no lugar de `HeroCard(me: me)`):

```dart
class _CapaSkeleton extends StatelessWidget {
  const _CapaSkeleton();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 220,
      decoration:
          const BoxDecoration(gradient: BrandTokens.gradientCapa),
      child: const Center(
        child: CircularProgressIndicator(color: Colors.white),
      ),
    );
  }
}

class _CachedCapaOrError extends StatelessWidget {
  const _CachedCapaOrError(this.ref);
  final WidgetRef ref;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<MeDto?>(
      future: LastKnownCache().readMe(),
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const _CapaSkeleton();
        }
        final me = snap.data;
        if (me != null) return HomeCapa(me: me);
        return Container(
          height: 220,
          decoration:
              const BoxDecoration(gradient: BrandTokens.gradientCapa),
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, color: Colors.white),
              const SizedBox(height: BrandTokens.spaceSm),
              const Text(
                'Não conseguimos carregar seus dados.',
                style: TextStyle(color: Colors.white),
              ),
              TextButton(
                onPressed: () => ref.invalidate(meProvider),
                child: const Text(
                  'Tentar de novo',
                  style: TextStyle(color: Colors.white),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
```

- [ ] **Step 4: Remover RedeDestaqueCard**

```bash
git rm lib/features/home/widgets/rede_destaque_card.dart test/rede_destaque_card_test.dart
```

Conferir com `grep -rn "rede_destaque" lib test` que não sobrou referência.

- [ ] **Step 5: Analyze + testes + commit**

Run: `flutter analyze` → `No issues found!`
Run: `flutter test` → `All tests passed!`

```bash
git add -A lib/features/home test/
git commit -m "feat(cliente): home vibrante — capa com rede integrada + FaturaCard, absorve RedeDestaqueCard"
```

---

### Task 9: Verificação final

**Files:**
- Nenhum novo (correções pontuais se a verificação apontar).

- [ ] **Step 1: Suite completa**

Run: `flutter analyze` → `No issues found!`
Run: `flutter test` → `All tests passed!`

- [ ] **Step 2: Build de sanidade**

Run: `flutter build apk --debug 2>&1 | tail -3`
Expected: `✓ Built build/app/outputs/flutter-apk/app-debug.apk` (se o ambiente local não tiver Android SDK, pular e anotar pro Robert validar no aparelho).

- [ ] **Step 3: Checklist manual (Robert, no aparelho, pós-push)**

- Login: capa + folha nos dois temas; CPF pré-preenchido no 2º acesso; "Esqueci minha senha" e "Criar conta" funcionam.
- Biometria: opt-in aparece 1x após login com senha; splash pede Face ID/digital; cancelar cai no login com botão "Entrar com biometria".
- Home: saudação certa pro horário; bloco de status com aparelhos + "Minha rede"; cliente sem ONU mapeada vê só status+plano; multi-contrato troca pelo endereço; fatura aberta mostra card com valor/vencimento; sem fatura, card some; todos os cards antigos aparecem rolando; pull-to-refresh e NPS ok; breaking bar aparece quando há manutenção.

- [ ] **Step 4: Push (somente com OK do Robert)**

```bash
git push origin main
```
