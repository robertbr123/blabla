import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/branding/blabla_logo.dart';

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
    final has = await ref.read(hasTokenProvider.future);
    await tick;
    if (!mounted) return;
    context.go(has ? '/os' : '/login');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Color(0xFF1d4ed8),
              Color(0xFF06b6d4),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: SafeArea(
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
                    child: const BlaBlaLogo.stacked(size: 120, light: true),
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
                              AlwaysStoppedAnimation<Color>(Colors.white70),
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
      ),
    );
  }
}
