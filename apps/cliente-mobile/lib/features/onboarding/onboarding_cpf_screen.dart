import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/auth_scaffold.dart';
import '../../core/ui/glass_card.dart';

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
    return AuthScaffold(
      icon: Icons.badge_outlined,
      title: 'Vamos te encontrar',
      subtitle: 'Digite seu CPF pra continuar.',
      child: GlassCard(
        child: GlassTextField(
          controller: _ctrl,
          label: 'CPF',
          autofocus: true,
          keyboardType: TextInputType.number,
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(11),
          ],
          textStyle: const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w700,
            fontSize: 22,
            letterSpacing: 2,
          ),
        ),
      ),
      bottom: Column(
        children: [
          GlassPrimaryButton(
            onPressed: _loading ? null : _continue,
            label: 'Continuar',
            loading: _loading,
            icon: Icons.arrow_forward_rounded,
          ),
          TextButton(
            onPressed: () => context.go('/login'),
            style: TextButton.styleFrom(
              foregroundColor: Colors.white,
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
