import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/auth_state.dart';
import '../../core/auth/auth_storage.dart';
import '../../core/auth/biometric_service.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/capa_folha.dart';
import '../../core/ui/formatters.dart';
import '../../core/ui/haptics.dart';
import '../../core/ui/sheet_text_field.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key, this.initialCpf});

  /// CPF pra pré-preencher (ex: veio do onboarding quando o CPF já tinha
  /// conta). Evita o cliente redigitar o que acabou de informar.
  final String? initialCpf;

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _cpfCtrl = TextEditingController();
  final _pwdCtrl = TextEditingController();
  bool _loading = false;
  bool _hide = true;
  bool _bioAvailable = false;

  @override
  void initState() {
    super.initState();
    final cpf = widget.initialCpf;
    if (cpf != null && cpf.length == 11) {
      _cpfCtrl.text = formatCpf(cpf);
    } else {
      // Sem CPF vindo do onboarding: tenta o último CPF logado (best-effort;
      // storage pode falhar em testes/simulador sem keychain — ignora).
      readLastCpf().then((saved) {
        if (!mounted || saved == null || saved.length != 11) return;
        if (_cpfCtrl.text.isNotEmpty) return;
        setState(() => _cpfCtrl.text = formatCpf(saved));
      }).catchError((_) {});
    }
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
  }

  @override
  void dispose() {
    _cpfCtrl.dispose();
    _pwdCtrl.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    final cpf = _cpfCtrl.text.replaceAll(RegExp(r'\D'), '');
    if (cpf.length != 11) {
      _toast('Informe um CPF válido');
      return;
    }
    if (_pwdCtrl.text.length < 8) {
      _toast('Senha curta');
      return;
    }
    setState(() => _loading = true);
    final r = await ref.read(authRepositoryProvider).login(
          cpf: cpf,
          password: _pwdCtrl.text,
        );
    if (!mounted) return;
    setState(() => _loading = false);
    switch (r) {
      case AuthOk():
        await Haptics.success();
        ref.read(authRefreshProvider).bump();
        if (!mounted) return;
        await _maybeOfferBiometria();
        if (!mounted) return;
        context.go('/home');
      case AuthError(:final message):
        await Haptics.error();
        _toast(message);
    }
  }

  Future<void> _forgot() async {
    final cpf = _cpfCtrl.text.replaceAll(RegExp(r'\D'), '');
    if (cpf.length != 11) {
      _toast('Informe seu CPF primeiro');
      return;
    }
    setState(() => _loading = true);
    await ref.read(authRepositoryProvider).forgot(cpf);
    if (!mounted) return;
    setState(() => _loading = false);
    _toast(
        'Se o CPF estiver cadastrado, você recebera um código no WhatsApp.');
    // Vai pra tela de reset (digita codigo + nova senha). Navega sempre, mesmo
    // se o CPF nao existir — preserva o "nao revelar se CPF existe"; o reset
    // simplesmente falha no codigo se nenhum OTP foi enviado.
    context.push('/forgot/reset', extra: {'cpf': cpf});
  }

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

  void _toast(String s) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

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
                      child: Stack(
                        children: [
                          // Marca d'água: logo grande, discreta, atrás do
                          // título — não intercepta toques.
                          Positioned.fill(
                            child: IgnorePointer(
                              child: Opacity(
                                opacity: 0.08,
                                child: Image.asset(
                                  'assets/icon/icon.png',
                                  fit: BoxFit.cover,
                                  alignment: Alignment.centerRight,
                                ),
                              ),
                            ),
                          ),
                          const Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text('Onde\nvocê',
                                  style: BrandTokens.displayTitle),
                              _PalavraRotativa(),
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
                        SheetTextField(
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
                        SheetTextField(
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
}

/// Terceira linha do título da capa: alterna entre palavras que completam
/// "Onde você ___" (estiver, morar, trabalhar...), reforçando o nome
/// Ondeline. Altura fixa pra não empurrar o layout ao trocar de palavra.
class _PalavraRotativa extends StatefulWidget {
  const _PalavraRotativa();

  @override
  State<_PalavraRotativa> createState() => _PalavraRotativaState();
}

class _PalavraRotativaState extends State<_PalavraRotativa> {
  static const _palavras = [
    'estiver.',
    'morar.',
    'trabalhar.',
    'estudar.',
    'precisar.',
  ];

  int _index = 0;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(milliseconds: 2800), (_) {
      if (!mounted) return;
      setState(() => _index = (_index + 1) % _palavras.length);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final palavra = _palavras[_index];
    return SizedBox(
      height: BrandTokens.displayTitle.fontSize! * BrandTokens.displayTitle.height!,
      child: ClipRect(
        child: Align(
          alignment: Alignment.centerLeft,
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 450),
            layoutBuilder: (currentChild, previousChildren) => Stack(
              alignment: Alignment.centerLeft,
              children: [
                ...previousChildren,
                if (currentChild != null) currentChild,
              ],
            ),
            transitionBuilder: (child, animation) => DualTransitionBuilder(
              animation: animation,
              // Palavra nova: entra de baixo pra cima, com fade-in.
              forwardBuilder: (context, animation, child) => FadeTransition(
                opacity: animation,
                child: SlideTransition(
                  position: Tween<Offset>(
                    begin: const Offset(0, 0.6),
                    end: Offset.zero,
                  )
                      .chain(CurveTween(curve: Curves.easeOutCubic))
                      .animate(animation),
                  child: child,
                ),
              ),
              // Palavra antiga: continua subindo (sai por cima), com fade-out.
              reverseBuilder: (context, animation, child) => FadeTransition(
                opacity: Tween<double>(begin: 1, end: 0).animate(animation),
                child: SlideTransition(
                  position: Tween<Offset>(
                    begin: Offset.zero,
                    end: const Offset(0, -0.6),
                  )
                      .chain(CurveTween(curve: Curves.easeInCubic))
                      .animate(animation),
                  child: child,
                ),
              ),
              child: child,
            ),
            child: Text(
              palavra,
              key: ValueKey(palavra),
              style: BrandTokens.displayTitle,
            ),
          ),
        ),
      ),
    );
  }
}
