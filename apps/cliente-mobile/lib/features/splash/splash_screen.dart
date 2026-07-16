import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_state.dart';
import '../../core/auth/auth_storage.dart';
import '../../core/auth/biometric_service.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/animated_gradient_background.dart';

class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _scale;
  late final Animation<double> _fade;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );
    _scale = Tween<double>(begin: 0.75, end: 1.0).animate(
      CurvedAnimation(parent: _ctrl, curve: Curves.easeOutBack),
    );
    _fade = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _ctrl, curve: Curves.easeOut),
    );
    _ctrl.forward();
    WidgetsBinding.instance.addPostFrameCallback((_) => _decide());
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _decide() async {
    await Future.delayed(const Duration(milliseconds: 1100));
    if (!mounted) return;
    final hasToken =
        await ref.read(hasTokenProvider.future).catchError((_) => false);
    if (!mounted) return;
    if (!hasToken) {
      context.go('/onboarding/cpf');
      return;
    }
    // Token válido: se o cliente ativou biometria, exige desbloqueio.
    final bioEnabled = await readBiometricEnabled().catchError((_) => false);
    if (!mounted) return;
    if (!bioEnabled) {
      context.go('/home');
      return;
    }
    final bio = ref.read(biometricServiceProvider);
    final ok = await bio.isAvailable() &&
        await bio.authenticate('Desbloqueie o app Ondeline');
    if (!mounted) return;
    // Falhou/cancelou: cai no login (senha ou nova tentativa de biometria).
    context.go(ok ? '/home' : '/login');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: BrandTokens.primaryDark,
      body: AnimatedGradientBackground(
        child: SafeArea(
          child: Center(
            child: AnimatedBuilder(
              animation: _ctrl,
              builder: (_, child) => Opacity(
                opacity: _fade.value,
                child: Transform.scale(scale: _scale.value, child: child),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    width: 120,
                    height: 120,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius:
                          BorderRadius.circular(BrandTokens.radiusXl),
                      boxShadow: BrandTokens.elevation3,
                    ),
                    padding: const EdgeInsets.all(BrandTokens.spaceMd),
                    child: ClipRRect(
                      borderRadius:
                          BorderRadius.circular(BrandTokens.radiusLg),
                      child: Image.asset(
                        'assets/icon/icon.png',
                        fit: BoxFit.contain,
                      ),
                    ),
                  ),
                  const SizedBox(height: BrandTokens.spaceLg),
                  const Text(
                    'Ondeline',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 30,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Sua internet, na palma da mão',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.75),
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.2,
                    ),
                  ),
                  const SizedBox(height: BrandTokens.spaceXxl),
                  const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
