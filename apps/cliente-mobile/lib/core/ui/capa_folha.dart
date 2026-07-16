import 'package:flutter/material.dart';

import '../branding/brand_tokens.dart';

/// Fundo "capa" da identidade vibrante: gradiente ciano + onda decorativa.
/// Usado no topo do login e da home.
class CapaBackground extends StatelessWidget {
  const CapaBackground({super.key, required this.child, this.padding});

  final Widget child;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(gradient: BrandTokens.gradientCapa),
      child: CustomPaint(
        painter: _WavePainter(),
        child: Padding(
          padding: padding ?? EdgeInsets.zero,
          child: child,
        ),
      ),
    );
  }
}

/// Duas ondas suaves em stroke branco de baixa opacidade, ancoradas no
/// terço inferior da capa — referência ao "onde" da Ondeline.
class _WavePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint1 = Paint()
      ..color = Colors.white.withValues(alpha: 0.16)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    final paint2 = Paint()
      ..color = Colors.white.withValues(alpha: 0.10)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;

    final y = size.height * 0.72;
    final w = size.width;

    Path onda(double baseY, double amp) {
      final p = Path()..moveTo(0, baseY);
      p.quadraticBezierTo(w * 0.17, baseY - amp, w * 0.33, baseY);
      p.quadraticBezierTo(w * 0.50, baseY + amp, w * 0.67, baseY);
      p.quadraticBezierTo(w * 0.83, baseY - amp, w, baseY);
      return p;
    }

    canvas.drawPath(onda(y, 14), paint1);
    canvas.drawPath(onda(y + 16, 12), paint2);
  }

  @override
  bool shouldRepaint(covariant _WavePainter oldDelegate) => false;
}

/// "Folha" clara com cantos superiores arredondados que sobrepõe a capa.
/// No dark mode vira folha azul-marinho (backgroundDark).
class FolhaContainer extends StatelessWidget {
  const FolhaContainer({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(BrandTokens.spaceMd),
    this.overlap = 0,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  /// Quantos pixels a folha sobe por cima da capa (margin-top negativa).
  final double overlap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final folha = Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: isDark ? BrandTokens.backgroundDark : BrandTokens.background,
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(BrandTokens.radiusFolha),
        ),
      ),
      padding: padding,
      child: child,
    );
    if (overlap == 0) return folha;
    return Transform.translate(offset: Offset(0, -overlap), child: folha);
  }
}

/// "Lábio" da folha: cantos superiores arredondados na cor da folha,
/// pintado por cima da capa (Positioned bottom: 0 dentro de um Stack), sem
/// Transform. Reproduz o padrão do Perfil (`_PerfilCapaDelegate`) — capa e
/// folha se encontram no mesmo box, sem fresta/corte.
class FolhaLip extends StatelessWidget {
  const FolhaLip({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      height: BrandTokens.radiusFolha,
      decoration: BoxDecoration(
        color: isDark ? BrandTokens.backgroundDark : BrandTokens.background,
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(BrandTokens.radiusFolha),
        ),
      ),
    );
  }
}
