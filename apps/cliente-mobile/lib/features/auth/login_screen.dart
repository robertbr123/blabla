import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';

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
      _toast('Informe um CPF valido');
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
        ref.read(authRefreshProvider).bump();
        context.go('/home');
      case AuthError(:final message):
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
        'Se o CPF estiver cadastrado, voce recebera um codigo no WhatsApp.');
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
                'Bem-vindo de volta',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Text(
                'Entre com seu CPF e senha.',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: BrandTokens.textSecondary,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceXl),
              TextField(
                controller: _cpfCtrl,
                keyboardType: TextInputType.number,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(11),
                ],
                decoration: const InputDecoration(labelText: 'CPF'),
              ),
              const SizedBox(height: BrandTokens.spaceMd),
              TextField(
                controller: _pwdCtrl,
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
              const SizedBox(height: BrandTokens.spaceSm),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: _loading ? null : _forgot,
                  child: const Text('Esqueci minha senha'),
                ),
              ),
              const Spacer(),
              FilledButton(
                onPressed: _loading ? null : _login,
                child: _loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Entrar'),
              ),
              TextButton(
                onPressed:
                    _loading ? null : () => context.go('/onboarding/cpf'),
                child: const Text('Criar conta'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
