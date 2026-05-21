import 'package:flutter/material.dart';

import 'brand_tokens.dart';

enum BrandTone { success, warning, info, danger, neutral }

enum BrandPillSize { sm, md }

/// Pill semântica: ícone + texto + bg tonal + ring. Espelha o
/// `OsStatusPill`/`ConversaStatusPill` da dashboard web.
///
/// Tone:
///   - success → emerald (OS concluída, sincronizado)
///   - warning → amber (em andamento, atenção)
///   - info → blue (pendente, aberto)
///   - danger → red (erro, cancelado)
///   - neutral → muted (encerrado, indefinido)
class BrandStatusPill extends StatelessWidget {
  final String label;
  final IconData icon;
  final BrandTone tone;
  final BrandPillSize size;

  const BrandStatusPill({
    super.key,
    required this.label,
    required this.icon,
    this.tone = BrandTone.neutral,
    this.size = BrandPillSize.md,
  });

  @override
  Widget build(BuildContext context) {
    final brand = context.brand;
    final scheme = Theme.of(context).colorScheme;

    final (bg, fg) = switch (tone) {
      BrandTone.success => (brand.successBg, brand.success),
      BrandTone.warning => (brand.warningBg, brand.warning),
      BrandTone.info => (brand.infoBg, brand.info),
      BrandTone.danger => (brand.dangerBg, brand.danger),
      BrandTone.neutral => (scheme.surfaceContainerHigh, scheme.onSurfaceVariant),
    };

    final sm = size == BrandPillSize.sm;
    final padding = sm
        ? const EdgeInsets.symmetric(horizontal: 8, vertical: 2)
        : const EdgeInsets.symmetric(horizontal: 10, vertical: 4);
    final iconSize = sm ? 12.0 : 14.0;
    final fontSize = sm ? 11.0 : 13.0;
    final gap = sm ? 4.0 : 6.0;

    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: fg.withValues(alpha: 0.3), width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: iconSize, color: fg),
          SizedBox(width: gap),
          Text(
            label,
            style: TextStyle(
              fontSize: fontSize,
              fontWeight: FontWeight.w500,
              color: fg,
            ),
          ),
        ],
      ),
    );
  }
}
