import 'dart:math' as math;
import 'package:flutter/material.dart';

import '../branding/brand_tokens.dart';

/// Fundo gradiente animado com blobs orgânicos em loop lento.
/// Usado nas telas de autenticação (login/onboarding) pra dar
/// personalidade visual sem custo de Lottie/asset.
class AnimatedGradientBackground extends StatefulWidget {
  const AnimatedGradientBackground({super.key, required this.child});
  final Widget child;

  @override
  State<AnimatedGradientBackground> createState() =>
      _AnimatedGradientBackgroundState();
}

class _AnimatedGradientBackgroundState extends State<AnimatedGradientBackground>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: BrandTokens.motionAmbient,
    )..repeat();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        // Gradiente base
        Positioned.fill(
          child: DecoratedBox(
            decoration: const BoxDecoration(
              gradient: BrandTokens.gradientAuthBg,
            ),
          ),
        ),
        // Blobs animados
        AnimatedBuilder(
          animation: _ctrl,
          builder: (_, __) {
            final t = _ctrl.value * 2 * math.pi;
            return Positioned.fill(
              child: CustomPaint(
                painter: _BlobsPainter(t: t),
              ),
            );
          },
        ),
        // Overlay sutil escurecendo embaixo — bem leve pra não criar banda visível
        Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                stops: const [0.0, 0.7, 1.0],
                colors: [
                  Colors.transparent,
                  Colors.transparent,
                  BrandTokens.primaryDark.withOpacity(0.12),
                ],
              ),
            ),
          ),
        ),
        widget.child,
      ],
    );
  }
}

class _BlobsPainter extends CustomPainter {
  _BlobsPainter({required this.t});
  final double t;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    // Blob 1 — ciano claro, canto superior esquerdo
    final p1 = Paint()
      ..color = BrandTokens.primaryLight.withOpacity(0.35)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 80);
    canvas.drawCircle(
      Offset(
        w * 0.2 + math.sin(t) * 30,
        h * 0.18 + math.cos(t * 0.7) * 30,
      ),
      w * 0.4,
      p1,
    );

    // Blob 2 — ciano puro, direita meio
    final p2 = Paint()
      ..color = BrandTokens.primary.withOpacity(0.35)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 100);
    canvas.drawCircle(
      Offset(
        w * 0.85 + math.cos(t * 1.1) * 40,
        h * 0.55 + math.sin(t * 0.9) * 50,
      ),
      w * 0.45,
      p2,
    );

    // Blob 3 — marinho, embaixo esquerda (bem difuso pra não formar banda)
    final p3 = Paint()
      ..color = const Color(0xFF1B4D8C).withOpacity(0.22) // tom exclusivo do blob de fundo da tela de auth
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 140);
    canvas.drawCircle(
      Offset(
        w * 0.1 + math.cos(t * 0.8) * 35,
        h * 1.05 + math.sin(t * 1.2) * 30,
      ),
      w * 0.5,
      p3,
    );
  }

  @override
  bool shouldRepaint(covariant _BlobsPainter oldDelegate) =>
      oldDelegate.t != t;
}
