import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/branding/brand_tokens.dart';

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
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Confirme seu telefone',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Text(
                'Enviamos um codigo de 6 digitos no WhatsApp ${widget.maskedPhone}.',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: BrandTokens.textSecondary,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceXl),
              TextField(
                controller: _ctrl,
                keyboardType: TextInputType.number,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      letterSpacing: 12,
                      fontWeight: FontWeight.w800,
                    ),
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(6),
                ],
                decoration: const InputDecoration(labelText: 'Codigo'),
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
                    : const Text('Validar codigo'),
              ),
              TextButton(
                onPressed: _loading ? null : _resend,
                child: const Text('Reenviar codigo'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
