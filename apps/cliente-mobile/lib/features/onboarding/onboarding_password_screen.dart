import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/haptics.dart';

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
      _toast('Senhas nao conferem');
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
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Crie uma senha',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Text(
                'No minimo 8 caracteres. Voce vai usar pra entrar no app.',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: BrandTokens.textSecondary,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceXl),
              TextField(
                controller: _p1,
                obscureText: _hide,
                decoration: InputDecoration(
                  labelText: 'Senha',
                  suffixIcon: IconButton(
                    icon: Icon(
                        _hide ? Icons.visibility : Icons.visibility_off),
                    onPressed: () => setState(() => _hide = !_hide),
                  ),
                ),
              ),
              const SizedBox(height: BrandTokens.spaceMd),
              TextField(
                controller: _p2,
                obscureText: _hide,
                decoration:
                    const InputDecoration(labelText: 'Confirme a senha'),
              ),
              const Spacer(),
              Padding(
                padding: const EdgeInsets.only(bottom: BrandTokens.spaceSm),
                child: Text.rich(
                  TextSpan(
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: BrandTokens.textSecondary,
                        ),
                    children: [
                      const TextSpan(
                          text: 'Ao criar a conta, voce concorda com os '),
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
                        text: 'Politica de Privacidade',
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
                child: _loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Criar conta'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
