import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/api/faturas_repository.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../../core/ui/pressable_scale.dart';
import '../../shell/main_shell.dart';

/// Primeiro card da folha: fatura em aberto mais urgente com CTA de pagar.
/// Auto-hide quando não há fatura aberta (estado "em dia" fica implícito
/// no status da capa) ou em erro/loading.
class FaturaCard extends ConsumerWidget {
  const FaturaCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final faturasAsync = ref.watch(faturasAbertasProvider);
    final fatura = faturasAsync.maybeWhen(
      data: (l) => l.isEmpty ? null : l.first,
      orElse: () => null,
    );
    if (fatura == null) return const SizedBox.shrink();

    final isDark = Theme.of(context).brightness == Brightness.dark;
    final venc = DateTime.tryParse(fatura.vencimento);
    final vencLabel =
        venc == null ? fatura.vencimento : DateFormat('dd/MM').format(venc);
    final valor = NumberFormat.currency(locale: 'pt_BR', symbol: r'R$')
        .format(fatura.valor);

    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceMd),
      child: PressableScale(
        onTap: () => ref.read(mainShellTabProvider.notifier).state = 1,
        child: Container(
          padding: const EdgeInsets.all(BrandTokens.spaceMd),
          decoration: BoxDecoration(
            color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
            borderRadius: BorderRadius.circular(BrandTokens.radiusMd + 2),
            border: Border.all(
              color: isDark ? Colors.white12 : BrandTokens.divider,
            ),
            boxShadow: BrandTokens.elevation2,
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'FATURA EM ABERTO',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.5,
                        color: isDark
                            ? BrandTokens.textSecondaryDark
                            : BrandTokens.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      valor,
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.5,
                      ),
                    ),
                    Text(
                      'vence em $vencLabel',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: isDark
                            ? BrandTokens.textSecondaryDark
                            : BrandTokens.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: BrandTokens.spaceMd,
                  vertical: 10,
                ),
                decoration: BoxDecoration(
                  color: BrandTokens.primary,
                  borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
                ),
                child: const Text(
                  'Pagar Pix',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
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
