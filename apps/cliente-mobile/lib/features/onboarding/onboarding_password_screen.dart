import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/auth_scaffold.dart';
import '../../core/ui/haptics.dart';
import '../../core/ui/sheet_text_field.dart';

class OnboardingPasswordScreen extends ConsumerStatefulWidget {
  const OnboardingPasswordScreen({
    super.key,
    required this.setupToken,
    required this.cpf,
  });
  final String setupToken;
  final String cpf;

  @override
  ConsumerState<OnboardingPasswordScreen> createState() =>
      _OnboardingPasswordScreenState();
}

class _OnboardingPasswordScreenState
    extends ConsumerState<OnboardingPasswordScreen> {
  final _p1 = TextEditingController();
  final _p2 = TextEditingController();
  bool _loading = false;
  bool _hide = true;

  @override
  void dispose() {
    _p1.dispose();
    _p2.dispose();
    super.dispose();
  }

  Future<void> _continue() async {
    if (_p1.text.length < 8) {
      _toast('Senha deve ter ao menos 8 caracteres');
      return;
    }
    if (_p1.text != _p2.text) {
      _toast('Senhas não conferem');
      return;
    }
    setState(() => _loading = true);
    final cpfDigits = widget.cpf.replaceAll(RegExp(r'\D'), '');
    final r = await ref.read(authRepositoryProvider).registerPassword(
          setupToken: widget.setupToken,
          password: _p1.text,
          cpfLast4: cpfDigits.substring(cpfDigits.length - 4),
          nome: '',
        );
    if (!mounted) return;
    setState(() => _loading = false);
    switch (r) {
      case AuthOk():
        await Haptics.success();
        ref.read(authRefreshProvider).bump();
        context.go('/onboarding/biometric');
      case AuthError(:final message):
        await Haptics.error();
        _toast(message);
    }
  }

  void _toast(String s) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    return AuthScaffold(
      showBack: true,
      icon: Icons.lock_outline_rounded,
      title: 'Crie uma senha',
      subtitle: 'No mínimo 8 caracteres. Você vai usar pra entrar no app.',
      child: Column(
        children: [
          SheetTextField(
            controller: _p1,
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
          const SizedBox(height: BrandTokens.spaceMd),
          SheetTextField(
            controller: _p2,
            label: 'Confirme a senha',
            obscureText: _hide,
            prefixIcon: Icons.lock_outline,
          ),
        ],
      ),
      bottom: Column(
        children: [
          Padding(
            padding: const EdgeInsets.only(bottom: BrandTokens.spaceSm),
            child: Text.rich(
              TextSpan(
                style: const TextStyle(
                  color: BrandTokens.textSecondary,
                  fontSize: 12,
                ),
                children: [
                  const TextSpan(
                      text: 'Ao criar a conta, você concorda com os '),
                  TextSpan(
                    text: 'Termos de Uso',
                    style: const TextStyle(
                      color: BrandTokens.primary,
                      fontWeight: FontWeight.w700,
                    ),
                    recognizer: TapGestureRecognizer()
                      ..onTap = () => context.push('/legal/termos'),
                  ),
                  const TextSpan(text: ' e a '),
                  TextSpan(
                    text: 'Política de Privacidade',
                    style: const TextStyle(
                      color: BrandTokens.primary,
                      fontWeight: FontWeight.w700,
                    ),
                    recognizer: TapGestureRecognizer()
                      ..onTap = () => context.push('/legal/privacidade'),
                  ),
                  const TextSpan(text: '.'),
                ],
              ),
              textAlign: TextAlign.center,
            ),
          ),
          FilledButton(
            onPressed: _loading ? null : _continue,
            style: FilledButton.styleFrom(
              backgroundColor: BrandTokens.primary,
              foregroundColor: Colors.white,
              minimumSize: const Size.fromHeight(52),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
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
                : const Text('Criar conta'),
          ),
          const SizedBox(height: BrandTokens.spaceXs),
        ],
      ),
    );
  }
}
