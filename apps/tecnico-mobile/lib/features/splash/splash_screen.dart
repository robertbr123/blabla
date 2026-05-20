import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/theme.dart';

/// Splash mostrado por ~1.2s enquanto o app boot (sync, firebase, etc).
/// Decide pra onde mandar baseado em hasTokenProvider.
class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen>
    with TickerProviderStateMixin {
  late final AnimationController _fadeCtrl;
  late final AnimationController _scaleCtrl;

  @override
  void initState() {
    super.initState();
    _fadeCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    )..forward();
    _scaleCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..forward();
    _navegarQuandoPronto();
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    _scaleCtrl.dispose();
    super.dispose();
  }

  Future<void> _navegarQuandoPronto() async {
    // Tempo minimo de splash pra o user ver o logo.
    final tick = Future<void>.delayed(const Duration(milliseconds: 1200));

    // Defensivo: se leitura do storage travar, nao deixa o app pendurado.
    // Em qualquer falha, manda pro /login (caminho mais seguro).
    bool has = false;
    bool biometric = false;
    try {
      has = await ref
          .read(hasTokenProvider.future)
          .timeout(const Duration(seconds: 5), onTimeout: () => false);
      final session = await ref
          .read(sessionSnapshotProvider.future)
          .timeout(const Duration(seconds: 5), onTimeout: () => null);
      biometric = session?.biometricEnabled ?? false;
    } catch (e) {
      debugPrint('splash._navegarQuandoPronto falhou: $e');
    }

    await tick;
    if (!mounted) return;
    if (!has) {
      context.go('/login');
      return;
    }
    if (biometric) {
      context.go('/reentry');
      return;
    }
    context.go('/os');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: brandInk,
      body: SafeArea(
        child: Stack(
          children: [
            Center(
              child: FadeTransition(
                opacity: CurvedAnimation(
                  parent: _fadeCtrl,
                  curve: Curves.easeOut,
                ),
                child: ScaleTransition(
                  scale: Tween(begin: 0.85, end: 1.0).animate(
                    CurvedAnimation(
                      parent: _scaleCtrl,
                      curve: Curves.easeOutBack,
                    ),
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(36),
                        child: Image.asset(
                          'assets/branding/app_icon.png',
                          width: 160,
                          height: 160,
                          fit: BoxFit.cover,
                        ),
                      ),
                      const SizedBox(height: 24),
                      const Text(
                        'BlaBla',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 36,
                          fontWeight: FontWeight.w800,
                          letterSpacing: -1.5,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'TÉCNICO',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.55),
                          fontSize: 12,
                          letterSpacing: 6,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            Positioned(
              left: 0,
              right: 0,
              bottom: 40,
              child: FadeTransition(
                opacity: CurvedAnimation(
                  parent: _fadeCtrl,
                  curve: const Interval(0.4, 1.0, curve: Curves.easeIn),
                ),
                child: const Column(
                  children: [
                    SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor:
                            AlwaysStoppedAnimation<Color>(brandGreenLight),
                      ),
                    ),
                    SizedBox(height: 12),
                    Text(
                      'Carregando…',
                      style: TextStyle(
                        color: Colors.white70,
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
