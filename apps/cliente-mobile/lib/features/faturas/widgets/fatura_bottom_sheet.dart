import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/api/dto.dart';
import '../../../core/api/faturas_repository.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../../core/ui/haptics.dart';

class FaturaBottomSheet extends ConsumerWidget {
  const FaturaBottomSheet({super.key, required this.fatura});
  final FaturaDto fatura;

  static Future<void> show(BuildContext context, FaturaDto fatura) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(BrandTokens.radiusXl),
        ),
      ),
      builder: (_) => FaturaBottomSheet(fatura: fatura),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final fmtValor = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
    final fmtData = DateFormat('dd/MM/yyyy', 'pt_BR');
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(BrandTokens.spaceLg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                margin: const EdgeInsets.only(bottom: BrandTokens.spaceLg),
                decoration: BoxDecoration(
                  color: BrandTokens.divider,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            Text(
              fmtValor.format(fatura.valor),
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: BrandTokens.spaceXs),
            Text(
              'Vence ${fmtData.format(fatura.vencimentoDate)}',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: BrandTokens.textSecondary,
                  ),
            ),
            const SizedBox(height: BrandTokens.spaceXl),
            if (fatura.temPix)
              FilledButton.icon(
                icon: const Icon(Icons.pix),
                label: const Text('Copiar codigo PIX'),
                onPressed: () => _copyPix(context, ref),
              ),
            if (fatura.temPix && fatura.temPdf)
              const SizedBox(height: BrandTokens.spaceSm),
            if (fatura.temPdf)
              OutlinedButton.icon(
                icon: const Icon(Icons.picture_as_pdf_outlined),
                label: const Text('Abrir boleto PDF'),
                onPressed: () => _openBoleto(context, ref),
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _copyPix(BuildContext context, WidgetRef ref) async {
    try {
      final codigo =
          await ref.read(faturasRepositoryProvider).getPix(fatura.id);
      await Clipboard.setData(ClipboardData(text: codigo));
      await Haptics.medium();
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Codigo PIX copiado')),
      );
    } catch (_) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Falha ao copiar PIX')),
      );
    }
  }

  Future<void> _openBoleto(BuildContext context, WidgetRef ref) async {
    try {
      final url =
          await ref.read(faturasRepositoryProvider).getBoletoUrl(fatura.id);
      final ok = await launchUrl(
        Uri.parse(url),
        mode: LaunchMode.externalApplication,
      );
      if (!ok && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Nao consegui abrir o boleto')),
        );
      }
    } catch (_) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Falha ao abrir boleto')),
      );
    }
  }
}
