import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_state.dart';
import '../../core/auth/auth_storage.dart';
import '../../core/auth/biometric_service.dart';
import '../../core/branding/brand_tokens.dart';

class OnboardingBiometricScreen extends ConsumerStatefulWidget {
  const OnboardingBiometricScreen({super.key});

  @override
  ConsumerState<OnboardingBiometricScreen> createState() =>
      _OnboardingBiometricScreenState();
}

class _OnboardingBiometricScreenState
    extends ConsumerState<OnboardingBiometricScreen> {
  bool _loading = false;

  Future<void> _enable() async {
    setState(() => _loading = true);
    final svc = ref.read(biometricServiceProvider);
    final ok = await svc.authenticate('Ative pra entrar mais rapido');
    if (ok) {
      await writeBiometricEnabled(true);
      ref.read(authRefreshProvider).bump();
    }
    if (!mounted) return;
    setState(() => _loading = false);
    context.go('/home');
  }

  void _skip() => context.go('/home');

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
              const SizedBox(height: BrandTokens.spaceXl),
              Center(
                child: Container(
                  width: 96,
                  height: 96,
                  decoration: BoxDecoration(
                    color: BrandTokens.primary.withOpacity(0.08),
                    borderRadius:
                        BorderRadius.circular(BrandTokens.radiusXl),
                  ),
                  child: const Icon(Icons.fingerprint,
                      size: 56, color: BrandTokens.primary),
                ),
              ),
              const SizedBox(height: BrandTokens.spaceLg),
              Text(
                'Quer entrar com biometria?',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Text(
                'Mais rapido e seguro. Voce ainda pode usar a senha quando quiser.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: BrandTokens.textSecondary,
                    ),
              ),
              const Spacer(),
              FilledButton(
                onPressed: _loading ? null : _enable,
                child: _loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Ativar biometria'),
              ),
              TextButton(
                onPressed: _loading ? null : _skip,
                child: const Text('Agora nao'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
