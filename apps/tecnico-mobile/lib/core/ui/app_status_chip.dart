import 'package:flutter/material.dart';

import '../branding/brand_tokens.dart';

enum AppStatusTone { neutral, info, success, warning, danger }

/// Chip semântico legado — agora usa tokens da marca (success/warning/info/danger).
/// Mantido pra compatibilidade com call sites existentes. Pra novos componentes,
/// use `BrandStatusPill` (com ícone).
class AppStatusChip extends StatelessWidget {
  const AppStatusChip({
    super.key,
    required this.label,
    this.tone = AppStatusTone.neutral,
  });

  final String label;
  final AppStatusTone tone;

  @override
  Widget build(BuildContext context) {
    final brand = context.brand;
    final scheme = Theme.of(context).colorScheme;
    final color = switch (tone) {
      AppStatusTone.info => brand.info,
      AppStatusTone.success => brand.success,
      AppStatusTone.warning => brand.warning,
      AppStatusTone.danger => brand.danger,
      AppStatusTone.neutral => scheme.onSurfaceVariant,
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.30)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: color,
          letterSpacing: 0.1,
        ),
      ),
    );
  }
}
