import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../core/api/dto.dart';
import '../../../core/branding/brand_tokens.dart';

class FaturaCard extends StatelessWidget {
  const FaturaCard({super.key, required this.fatura, required this.onTap});
  final FaturaDto fatura;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final fmtValor = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
    final fmtData = DateFormat('dd/MM/yyyy', 'pt_BR');
    final chip = _statusChip(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
      child: Container(
        margin: const EdgeInsets.only(bottom: BrandTokens.spaceMd),
        padding: const EdgeInsets.all(BrandTokens.spaceLg),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
          boxShadow: BrandTokens.shadowCard,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    fmtValor.format(fatura.valor),
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                ),
                chip,
              ],
            ),
            const SizedBox(height: BrandTokens.spaceSm),
            Row(
              children: [
                const Icon(Icons.calendar_today_outlined,
                    size: 16, color: BrandTokens.textSecondary),
                const SizedBox(width: BrandTokens.spaceXs),
                Text(
                  'Vence ${fmtData.format(fatura.vencimentoDate)}',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: BrandTokens.textSecondary,
                      ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _statusChip(BuildContext context) {
    final (label, color) = switch (fatura.status) {
      'pago' => ('Pago', BrandTokens.success),
      'aberto' when fatura.isVencido => ('Vencido', BrandTokens.danger),
      'aberto' => ('Em aberto', BrandTokens.info),
      _ => (fatura.status, BrandTokens.textSecondary),
    };
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: BrandTokens.spaceSm,
        vertical: 4,
      ),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.w700,
          fontSize: 12,
        ),
      ),
    );
  }
}
