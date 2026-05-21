import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../core/api/dto.dart';
import '../../../core/branding/brand_tokens.dart';

class OsCard extends StatelessWidget {
  const OsCard({super.key, required this.os});
  final OsDto os;

  @override
  Widget build(BuildContext context) {
    final fmt = DateFormat('dd/MM/yyyy HH:mm', 'pt_BR');
    final (statusLabel, statusColor) = switch (os.status) {
      'aberto' => ('Aberto', BrandTokens.info),
      'em_atendimento' => ('Em atendimento', BrandTokens.warning),
      'concluido' => ('Concluido', BrandTokens.success),
      'cancelado' => ('Cancelado', BrandTokens.textSecondary),
      _ => (os.status, BrandTokens.textSecondary),
    };
    return Container(
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
                  os.tipoLabel,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: BrandTokens.spaceSm,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
                ),
                child: Text(
                  statusLabel,
                  style: TextStyle(
                    color: statusColor,
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                  ),
                ),
              ),
            ],
          ),
          if (os.descricao.isNotEmpty) ...[
            const SizedBox(height: BrandTokens.spaceSm),
            Text(
              os.descricao,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: BrandTokens.textSecondary,
                  ),
            ),
          ],
          const SizedBox(height: BrandTokens.spaceSm),
          Text(
            'Aberto em ${fmt.format(os.createdAt.toLocal())}',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: BrandTokens.textSecondary,
                ),
          ),
        ],
      ),
    );
  }
}
