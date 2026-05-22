import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/auth_scaffold.dart';
import '../../core/ui/glass_card.dart';

class OnboardingOtpScreen extends ConsumerStatefulWidget {
  const OnboardingOtpScreen({
    super.key,
    required this.cpf,
    required this.maskedPhone,
  });
  final String cpf;
  final String maskedPhone;

  @override
  ConsumerState<OnboardingOtpScreen> createState() =>
      _OnboardingOtpScreenState();
}

class _OnboardingOtpScreenState extends ConsumerState<OnboardingOtpScreen> {
  final _ctrl = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _continue() async {
    final code = _ctrl.text.trim();
    if (code.length != 6) {
      _toast('Codigo deve ter 6 digitos');
      return;
    }
    setState(() => _loading = true);
    final r =
        await ref.read(authRepositoryProvider).registerVerify(widget.cpf, code);
    if (!mounted) return;
    setState(() => _loading = false);
    switch (r) {
      case RegisterVerifyOk(:final setupToken):
        context.push('/onboarding/password', extra: {
          'setup_token': setupToken,
          'cpf': widget.cpf,
        });
      case RegisterVerifyError(:final message):
        _toast(message);
    }
  }

  Future<void> _resend() async {
    setState(() => _loading = true);
    await ref.read(authRepositoryProvider).registerStart(widget.cpf);
    if (!mounted) return;
    setState(() => _loading = false);
    _toast('Codigo reenviado');
  }

  void _toast(String s) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    return AuthScaffold(
      showBack: true,
      icon: Icons.message_outlined,
      title: 'Confirme seu telefone',
      subtitle:
          'Enviamos um codigo de 6 digitos no WhatsApp ${widget.maskedPhone}.',
      child: GlassCard(
        child: GlassTextField(
          controller: _ctrl,
          label: 'Codigo',
          autofocus: true,
          keyboardType: TextInputType.number,
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(6),
          ],
          textStyle: const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w800,
            fontSize: 28,
            letterSpacing: 14,
          ),
        ),
      ),
      bottom: Column(
        children: [
          GlassPrimaryButton(
            onPressed: _loading ? null : _continue,
            label: 'Validar codigo',
            loading: _loading,
            icon: Icons.check_rounded,
          ),
          TextButton(
            onPressed: _loading ? null : _resend,
            style: TextButton.styleFrom(
              foregroundColor: Colors.white,
              minimumSize: const Size.fromHeight(48),
            ),
            child: const Text(
              'Reenviar codigo',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(height: BrandTokens.spaceXs),
        ],
      ),
    );
  }
}
