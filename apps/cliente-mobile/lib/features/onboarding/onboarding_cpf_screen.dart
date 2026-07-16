import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/auth_scaffold.dart';
import '../../core/ui/formatters.dart';
import '../../core/ui/sheet_text_field.dart';

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
      _toast('Informe um CPF válido com 11 digitos');
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
        final lower = message.toLowerCase();
        if (lower.contains('cadastrad')) {
          _toast('Esse CPF já tem conta. Vou te levar pro login.');
          await Future.delayed(const Duration(milliseconds: 700));
          if (!mounted) return;
          // Leva o CPF junto pro login já vir preenchido.
          context.go('/login', extra: {'cpf': cpf});
        } else {
          _toast(message);
        }
    }
  }

  void _toast(String s) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return AuthScaffold(
      icon: Icons.badge_outlined,
      title: 'Vamos te encontrar',
      subtitle: 'Digite o CPF do titular do contrato pra gente localizar seu cadastro.',
      child: Column(
        children: [
          SheetTextField(
            controller: _ctrl,
            label: 'CPF',
            autofocus: true,
            keyboardType: TextInputType.number,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(11),
              CpfFormatter(),
            ],
            prefixIcon: Icons.badge_outlined,
          ),
          Container(
            margin: const EdgeInsets.only(top: BrandTokens.spaceLg),
            padding: const EdgeInsets.all(BrandTokens.spaceMd),
            decoration: BoxDecoration(
              color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isDark ? Colors.white12 : BrandTokens.divider,
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.verified_user_outlined,
                    color: BrandTokens.primary, size: 22),
                const SizedBox(width: BrandTokens.spaceSm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Por que pedimos seu CPF?',
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
                      const SizedBox(height: 2),
                      Text(
                        'Usamos só pra localizar seu contrato na Ondeline. Seus dados ficam protegidos.',
                        style: TextStyle(
                          fontSize: 12,
                          color: isDark
                              ? BrandTokens.textSecondaryDark
                              : BrandTokens.textSecondary,
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
      bottom: Column(
        children: [
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
                : const Text('Continuar'),
          ),
          TextButton(
            onPressed: () {
              // Se já digitou um CPF válido, leva pro login pré-preenchido.
              final cpf = _ctrl.text.replaceAll(RegExp(r'\D'), '');
              context.go(
                '/login',
                extra: cpf.length == 11 ? {'cpf': cpf} : null,
              );
            },
            style: TextButton.styleFrom(
              minimumSize: const Size.fromHeight(48),
            ),
            child: const Text(
              'Ja tenho conta',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(height: BrandTokens.spaceXs),
        ],
      ),
    );
  }
}
