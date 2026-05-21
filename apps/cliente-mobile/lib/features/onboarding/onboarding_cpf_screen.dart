import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/dev/dev_mode.dart';

class OnboardingCpfScreen extends ConsumerStatefulWidget {
  const OnboardingCpfScreen({super.key});

  @override
  ConsumerState<OnboardingCpfScreen> createState() =>
      _OnboardingCpfScreenState();
}

class _OnboardingCpfScreenState extends ConsumerState<OnboardingCpfScreen> {
  final _ctrl = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _continue() async {
    final cpf = _ctrl.text.replaceAll(RegExp(r'\D'), '');
    if (cpf.length != 11) {
      _toast('Informe um CPF valido com 11 digitos');
      return;
    }
    setState(() => _loading = true);
    final r = await ref.read(authRepositoryProvider).registerStart(cpf);
    if (!mounted) return;
    setState(() => _loading = false);
    switch (r) {
      case RegisterStartOk(:final maskedPhone):
        context.push('/onboarding/otp', extra: {
          'cpf': cpf,
          'masked_phone': maskedPhone,
        });
      case RegisterStartError(:final message):
        if (message.toLowerCase().contains('ja cadastrado')) {
          context.go('/login');
        } else {
          _toast(message);
        }
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
                'Vamos te encontrar',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Text(
                'Digite seu CPF pra continuar.',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: BrandTokens.textSecondary,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceXl),
              TextField(
                controller: _ctrl,
                keyboardType: TextInputType.number,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(11),
                ],
                decoration: const InputDecoration(labelText: 'CPF'),
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const Spacer(),
              FilledButton(
                onPressed: _loading ? null : _continue,
                child: _loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Continuar'),
              ),
              TextButton(
                onPressed: () => context.go('/login'),
                child: const Text('Ja tenho conta'),
              ),
              const SizedBox(height: BrandTokens.spaceLg),
              const Divider(),
              const SizedBox(height: BrandTokens.spaceSm),
              OutlinedButton.icon(
                icon: const Icon(Icons.bug_report_outlined),
                label: const Text('Entrar em modo dev (sem rede)'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: BrandTokens.warning,
                  side: const BorderSide(color: BrandTokens.warning),
                ),
                onPressed: _loading
                    ? null
                    : () async {
                        await ref.read(devModeProvider).enable();
                        ref.read(authRefreshProvider).bump();
                        if (!mounted) return;
                        context.go('/home');
                      },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
