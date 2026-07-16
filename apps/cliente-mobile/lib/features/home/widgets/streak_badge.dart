import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/streak_repository.dart';
import '../../../core/branding/brand_tokens.dart';

/// Badge "🔥 N meses pagando em dia" — auto-hide quando streak < 3.
class StreakBadge extends ConsumerWidget {
  const StreakBadge({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(streakProvider);
    return async.maybeWhen(
      data: (s) {
        if (s.atual < 3) return const SizedBox.shrink();
        final isDark = Theme.of(context).brightness == Brightness.dark;
        final divider = isDark ? Colors.white10 : BrandTokens.divider;
        return Container(
          decoration: BoxDecoration(
            border: Border(top: BorderSide(color: divider)),
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: BrandTokens.spaceMd,
            vertical: 10,
          ),
          child: Row(
            children: [
              const Text('🔥', style: TextStyle(fontSize: 16)),
              const SizedBox(width: 6),
              Expanded(
                child: RichText(
                  text: TextSpan(
                    style: const TextStyle(
                      color: BrandTokens.textSecondary,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                    children: [
                      TextSpan(
                        text: '${s.atual} ',
                        style: const TextStyle(
                          color: BrandTokens.warning,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      TextSpan(
                        text: s.atual == 1
                            ? 'mês pagando em dia'
                            : 'meses pagando em dia',
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
      orElse: () => const SizedBox.shrink(),
    );
  }
}
