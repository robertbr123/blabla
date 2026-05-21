import 'package:flutter/material.dart';

import 'brand_status_pill.dart' show BrandTone;
import 'brand_theme.dart';
import 'brand_tokens.dart';

/// Cartão de KPI: label (caps 11px), valor (28px tabular), ícone num quadrado
/// tintado 36×36. Espelha o `<Kpi>` do dashboard.
class BrandKpiCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final BrandTone tone;
  final VoidCallback? onTap;

  const BrandKpiCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    this.tone = BrandTone.neutral,
    this.onTap,
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

    return Material(
      color: scheme.surfaceContainer,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: scheme.outlineVariant),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Text(
                      label.toUpperCase(),
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.5,
                        color: scheme.onSurfaceVariant,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Container(
                    width: 32,
                    height: 32,
                    decoration: BoxDecoration(
                      color: bg,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(icon, size: 16, color: fg),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                value,
                style: tabularStyle(TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.w700,
                  height: 1.0,
                  color: scheme.onSurface,
                )),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
