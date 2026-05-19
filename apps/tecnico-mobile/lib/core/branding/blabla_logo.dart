import 'package:flutter/material.dart';

/// Logo do BlaBla — dois baloes de chat sobrepostos.
///
/// Modes:
/// - `BlaBlaLogo.mark()` — so o icone (quadrado), bom pra app icon e avatar
/// - `BlaBlaLogo.full()` — icone + wordmark "blabla", bom pra header/login
/// - `BlaBlaLogo.stacked()` — icone em cima do wordmark, bom pra splash
class BlaBlaLogo extends StatelessWidget {
  final double size;
  final _LogoMode mode;
  final bool light;

  const BlaBlaLogo.mark({super.key, this.size = 64, this.light = false})
      : mode = _LogoMode.mark;

  const BlaBlaLogo.full({super.key, this.size = 56, this.light = false})
      : mode = _LogoMode.full;

  const BlaBlaLogo.stacked({super.key, this.size = 96, this.light = false})
      : mode = _LogoMode.stacked;

  @override
  Widget build(BuildContext context) {
    final brandStart = light ? Colors.white : const Color(0xFF2563eb);
    final brandEnd = light ? Colors.white : const Color(0xFF06b6d4);

    final mark = _LogoMark(
      size: size,
      gradientStart: brandStart,
      gradientEnd: brandEnd,
    );

    final word = _Wordmark(
      fontSize: size * 0.42,
      color: light ? Colors.white : const Color(0xFF0f172a),
      accent: brandEnd,
    );

    switch (mode) {
      case _LogoMode.mark:
        return mark;
      case _LogoMode.full:
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [mark, SizedBox(width: size * 0.18), word],
        );
      case _LogoMode.stacked:
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            mark,
            SizedBox(height: size * 0.20),
            _Wordmark(
              fontSize: size * 0.32,
              color: light ? Colors.white : const Color(0xFF0f172a),
              accent: brandEnd,
            ),
          ],
        );
    }
  }
}

enum _LogoMode { mark, full, stacked }

class _LogoMark extends StatelessWidget {
  final double size;
  final Color gradientStart;
  final Color gradientEnd;

  const _LogoMark({
    required this.size,
    required this.gradientStart,
    required this.gradientEnd,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        painter: _LogoMarkPainter(
          gradientStart: gradientStart,
          gradientEnd: gradientEnd,
        ),
      ),
    );
  }
}

class _LogoMarkPainter extends CustomPainter {
  final Color gradientStart;
  final Color gradientEnd;

  _LogoMarkPainter({required this.gradientStart, required this.gradientEnd});

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    final gradient = LinearGradient(
      colors: [gradientStart, gradientEnd],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    );

    // Balão de fundo (maior, à direita-em cima).
    final back = _bubblePath(
      Rect.fromLTWH(w * 0.18, h * 0.06, w * 0.78, h * 0.78),
      tailDirection: _Tail.bottomRight,
      tailSize: w * 0.16,
      radius: w * 0.24,
    );
    final paintBack = Paint()
      ..shader = gradient
          .createShader(Rect.fromLTWH(0, 0, w, h))
      ..isAntiAlias = true;
    canvas.drawPath(back, paintBack);

    // Balão da frente (menor, à esquerda-em baixo) — branco com leve sombra.
    final front = _bubblePath(
      Rect.fromLTWH(w * 0.04, h * 0.18, w * 0.66, h * 0.66),
      tailDirection: _Tail.bottomLeft,
      tailSize: w * 0.14,
      radius: w * 0.20,
    );
    final paintShadow = Paint()
      ..color = const Color(0x33000000)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6)
      ..isAntiAlias = true;
    canvas.drawPath(front.shift(Offset(0, h * 0.02)), paintShadow);

    final paintFront = Paint()
      ..color = Colors.white
      ..isAntiAlias = true;
    canvas.drawPath(front, paintFront);

    // 3 pontinhos dentro do balão da frente (típico "..."  do chat).
    final dotsY = h * 0.49;
    final dotR = w * 0.045;
    final centerX = w * 0.37;
    final spacing = w * 0.12;
    final dotsPaint = Paint()..shader = gradient.createShader(
        Rect.fromLTWH(0, 0, w, h));
    for (int i = -1; i <= 1; i++) {
      canvas.drawCircle(Offset(centerX + i * spacing, dotsY), dotR, dotsPaint);
    }
  }

  Path _bubblePath(
    Rect rect, {
    required _Tail tailDirection,
    required double tailSize,
    required double radius,
  }) {
    final rrect = RRect.fromRectAndRadius(rect, Radius.circular(radius));
    final path = Path()..addRRect(rrect);

    final tail = Path();
    switch (tailDirection) {
      case _Tail.bottomLeft:
        tail.moveTo(rect.left + rect.width * 0.18, rect.bottom - 4);
        tail.quadraticBezierTo(
          rect.left + tailSize * 0.4,
          rect.bottom + tailSize * 0.9,
          rect.left + rect.width * 0.05,
          rect.bottom + tailSize * 0.4,
        );
        tail.lineTo(rect.left + rect.width * 0.32, rect.bottom - 2);
        tail.close();
        break;
      case _Tail.bottomRight:
        tail.moveTo(rect.right - rect.width * 0.20, rect.bottom - 4);
        tail.quadraticBezierTo(
          rect.right - tailSize * 0.3,
          rect.bottom + tailSize * 0.9,
          rect.right - rect.width * 0.04,
          rect.bottom + tailSize * 0.5,
        );
        tail.lineTo(rect.right - rect.width * 0.34, rect.bottom - 2);
        tail.close();
        break;
    }

    return Path.combine(PathOperation.union, path, tail);
  }

  @override
  bool shouldRepaint(covariant _LogoMarkPainter old) =>
      old.gradientStart != gradientStart || old.gradientEnd != gradientEnd;
}

enum _Tail { bottomLeft, bottomRight }

class _Wordmark extends StatelessWidget {
  final double fontSize;
  final Color color;
  final Color accent;

  const _Wordmark({
    required this.fontSize,
    required this.color,
    required this.accent,
  });

  @override
  Widget build(BuildContext context) {
    return RichText(
      text: TextSpan(
        style: TextStyle(
          fontSize: fontSize,
          fontWeight: FontWeight.w800,
          color: color,
          letterSpacing: -1,
          height: 1,
        ),
        children: [
          const TextSpan(text: 'bla'),
          TextSpan(
            text: 'bla',
            style: TextStyle(color: accent),
          ),
        ],
      ),
    );
  }
}
