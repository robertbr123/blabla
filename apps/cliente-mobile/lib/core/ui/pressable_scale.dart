import 'package:flutter/material.dart';

import '../branding/brand_tokens.dart';

/// Encolhe o child levemente enquanto pressionado (feel iOS).
/// Não substitui InkWell — envolve por fora (escala o card inteiro,
/// incluindo sombra/gradiente).
class PressableScale extends StatefulWidget {
  const PressableScale({
    super.key,
    required this.child,
    this.onTap,
    this.scale = 0.97,
  });

  final Widget child;
  final VoidCallback? onTap;
  final double scale;

  @override
  State<PressableScale> createState() => _PressableScaleState();
}

class _PressableScaleState extends State<PressableScale> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapDown: (_) => setState(() => _pressed = true),
      onTapCancel: () => setState(() => _pressed = false),
      onTapUp: (_) => setState(() => _pressed = false),
      onTap: widget.onTap,
      child: AnimatedScale(
        duration: BrandTokens.motionFast,
        curve: Curves.easeOut,
        scale: _pressed ? widget.scale : 1.0,
        child: widget.child,
      ),
    );
  }
}
