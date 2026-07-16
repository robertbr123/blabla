import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_state.dart';
import '../../core/auth/auth_storage.dart';
import '../../core/auth/biometric_service.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/auth_scaffold.dart';

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
    return AuthScaffold(
      icon: Icons.fingerprint,
      title: 'Quer entrar com biometria?',
      subtitle:
          'Mais rapido e seguro. Você ainda pode usar a senha quando quiser.',
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: BrandTokens.spaceLg),
        child: Column(
          children: [
            Container(
              width: 96,
              height: 96,
              decoration: BoxDecoration(
                color: BrandTokens.primary.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(BrandTokens.radiusXl),
                border: Border.all(
                  color: BrandTokens.primary.withValues(alpha: 0.24),
                ),
              ),
              child: const Icon(
                Icons.fingerprint,
                size: 56,
                color: BrandTokens.primary,
              ),
            ),
            const SizedBox(height: BrandTokens.spaceMd),
            const Text(
              'Sua digital ou Face ID protegem seu acesso.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: BrandTokens.textPrimary,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
      bottom: Column(
        children: [
          FilledButton(
            onPressed: _loading ? null : _enable,
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
                : const Text('Ativar biometria'),
          ),
          TextButton(
            onPressed: _loading ? null : _skip,
            style: TextButton.styleFrom(
              minimumSize: const Size.fromHeight(48),
            ),
            child: const Text(
              'Agora não',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(height: BrandTokens.spaceXs),
        ],
      ),
    );
  }
}
