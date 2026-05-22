import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_state.dart';
import '../../core/auth/auth_storage.dart';
import '../../core/auth/biometric_service.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/auth_scaffold.dart';
import '../../core/ui/glass_card.dart';

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
          'Mais rapido e seguro. Voce ainda pode usar a senha quando quiser.',
      child: GlassCard(
        padding: const EdgeInsets.all(BrandTokens.spaceXl),
        child: Column(
          children: [
            Container(
              width: 96,
              height: 96,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.10),
                borderRadius: BorderRadius.circular(BrandTokens.radiusXl),
                border: Border.all(
                  color: Colors.white.withOpacity(0.18),
                ),
              ),
              child: const Icon(
                Icons.fingerprint,
                size: 56,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: BrandTokens.spaceMd),
            const Text(
              'Sua digital ou Face ID protegem seu acesso.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
      bottom: Column(
        children: [
          GlassPrimaryButton(
            onPressed: _loading ? null : _enable,
            label: 'Ativar biometria',
            loading: _loading,
            icon: Icons.fingerprint,
          ),
          TextButton(
            onPressed: _loading ? null : _skip,
            style: TextButton.styleFrom(
              foregroundColor: Colors.white,
              minimumSize: const Size.fromHeight(48),
            ),
            child: const Text(
              'Agora nao',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(height: BrandTokens.spaceXs),
        ],
      ),
    );
  }
}
