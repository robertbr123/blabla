import 'package:flutter/material.dart';

import '../../../core/api/dto.dart';
import '../../../core/branding/brand_tokens.dart';

class AvisosList extends StatelessWidget {
  const AvisosList({super.key, required this.avisos});
  final List<AvisoDto> avisos;

  @override
  Widget build(BuildContext context) {
    if (avisos.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Avisos',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w800,
              ),
        ),
        const SizedBox(height: BrandTokens.spaceSm),
        ...avisos.map(_card),
      ],
    );
  }

  Widget _card(AvisoDto a) {
    return Builder(
      builder: (ctx) {
        final color = switch (a.severidade) {
          'danger' => BrandTokens.danger,
          'warning' => BrandTokens.warning,
          _ => BrandTokens.info,
        };
        return Container(
          margin: const EdgeInsets.only(bottom: BrandTokens.spaceSm),
          padding: const EdgeInsets.all(BrandTokens.spaceMd),
          decoration: BoxDecoration(
            color: color.withOpacity(0.08),
            borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
            border: Border.all(color: color.withOpacity(0.25)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                a.titulo,
                style: TextStyle(fontWeight: FontWeight.w700, color: color),
              ),
              const SizedBox(height: BrandTokens.spaceXs),
              Text(a.corpo),
            ],
          ),
        );
      },
    );
  }
}
