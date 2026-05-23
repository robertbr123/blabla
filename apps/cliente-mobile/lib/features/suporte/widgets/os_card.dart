import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/api/dto.dart';
import '../../../core/api/os_repository.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../nps/nps_bottom_sheet.dart';

/// UUID curto pro display — pega os primeiros 6 chars do id da OS.
/// Suficiente pro cliente identificar visualmente, sem expor o uuid inteiro.
String _numeroCurto(String osId) {
  final clean = osId.replaceAll('-', '');
  return clean.length <= 6 ? clean.toUpperCase() : clean.substring(0, 6).toUpperCase();
}

class OsCard extends ConsumerWidget {
  const OsCard({super.key, required this.os});
  final OsDto os;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
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
          if (os.npsPendente) ...[
            const SizedBox(height: BrandTokens.spaceMd),
            _AvaliarCta(
              osId: os.id,
              tipoLabel: os.tipoLabel,
              numero: _numeroCurto(os.id),
              teveVisitaTecnica: os.teveVisitaTecnica,
              onRespondido: () {
                ref.invalidate(osListProvider);
              },
            ),
          ],
        ],
      ),
    );
  }
}

class _AvaliarCta extends StatelessWidget {
  const _AvaliarCta({
    required this.osId,
    required this.tipoLabel,
    required this.numero,
    required this.teveVisitaTecnica,
    required this.onRespondido,
  });
  final String osId;
  final String tipoLabel;
  final String numero;
  final bool teveVisitaTecnica;
  final VoidCallback onRespondido;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: BrandTokens.primary.withOpacity(0.10),
      borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
      child: InkWell(
        borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
        onTap: () async {
          await showNpsBottomSheet(
            context,
            osId: osId,
            tipoLabel: tipoLabel,
            numero: numero,
            teveVisitaTecnica: teveVisitaTecnica,
          );
          onRespondido();
        },
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: BrandTokens.spaceMd,
            vertical: BrandTokens.spaceSm + 2,
          ),
          child: Row(
            children: [
              const Icon(
                Icons.star_rounded,
                color: BrandTokens.primary,
                size: 20,
              ),
              const SizedBox(width: BrandTokens.spaceSm),
              const Expanded(
                child: Text(
                  'Avaliar atendimento',
                  style: TextStyle(
                    color: BrandTokens.primary,
                    fontWeight: FontWeight.w800,
                    fontSize: 14,
                  ),
                ),
              ),
              const Icon(
                Icons.chevron_right_rounded,
                color: BrandTokens.primary,
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
