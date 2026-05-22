import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/animated_gradient_background.dart';
import '../../core/ui/glass_card.dart';
import '../../core/ui/haptics.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _cpfCtrl = TextEditingController();
  final _pwdCtrl = TextEditingController();
  bool _loading = false;
  bool _hide = true;

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
  }

  void _toast(String s) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: BrandTokens.primaryDark,
      body: AnimatedGradientBackground(
        child: SafeArea(
          child: GestureDetector(
            onTap: () => FocusScope.of(context).unfocus(),
            behavior: HitTestBehavior.translucent,
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(
                horizontal: BrandTokens.spaceLg,
                vertical: BrandTokens.spaceXl,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: BrandTokens.spaceXl),
                  // Logo / ícone marca
                  Center(
                    child: Container(
                      width: 72,
                      height: 72,
                      decoration: BoxDecoration(
                        gradient: BrandTokens.gradientPrimary,
                        borderRadius:
                            BorderRadius.circular(BrandTokens.radiusLg),
                        boxShadow: BrandTokens.shadowColored,
                      ),
                      child: const Icon(
                        Icons.wifi_rounded,
                        color: Colors.white,
                        size: 38,
                      ),
                    ),
                  ),
                  const SizedBox(height: BrandTokens.spaceLg),
                  const Text(
                    'Bem-vindo de volta',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                      fontSize: 28,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: BrandTokens.spaceXs),
                  const Text(
                    'Entre com seu CPF e senha pra continuar.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white70,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: BrandTokens.spaceXl),
                  GlassCard(
                    child: Column(
                      children: [
                        GlassTextField(
                          controller: _cpfCtrl,
                          label: 'CPF',
                          keyboardType: TextInputType.number,
                          inputFormatters: [
                            FilteringTextInputFormatter.digitsOnly,
                            LengthLimitingTextInputFormatter(11),
                          ],
                          prefixIcon: const Icon(
                            Icons.badge_outlined,
                            color: Colors.white70,
                            size: 20,
                          ),
                        ),
                        const SizedBox(height: BrandTokens.spaceMd),
                        GlassTextField(
                          controller: _pwdCtrl,
                          label: 'Senha',
                          obscureText: _hide,
                          prefixIcon: const Icon(
                            Icons.lock_outline,
                            color: Colors.white70,
                            size: 20,
                          ),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _hide
                                  ? Icons.visibility_outlined
                                  : Icons.visibility_off_outlined,
                              color: Colors.white70,
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
                              foregroundColor: BrandTokens.primaryLight,
                              padding: EdgeInsets.zero,
                              tapTargetSize:
                                  MaterialTapTargetSize.shrinkWrap,
                            ),
                            child: const Text(
                              'Esqueci minha senha',
                              style: TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: BrandTokens.spaceLg),
                  GlassPrimaryButton(
                    onPressed: _loading ? null : _login,
                    label: 'Entrar',
                    loading: _loading,
                    icon: Icons.arrow_forward_rounded,
                  ),
                  const SizedBox(height: BrandTokens.spaceMd),
                  TextButton(
                    onPressed:
                        _loading ? null : () => context.go('/onboarding/cpf'),
                    style: TextButton.styleFrom(
                      foregroundColor: Colors.white,
                      minimumSize: const Size.fromHeight(48),
                    ),
                    child: const Text(
                      'Criar conta',
                      style: TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
