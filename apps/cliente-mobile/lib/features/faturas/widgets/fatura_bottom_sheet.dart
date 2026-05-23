import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/api/dto.dart';
import '../../../core/api/faturas_repository.dart';
import '../../../core/api/me_repository.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../../core/share/render_to_png.dart';
import '../../../core/ui/haptics.dart';
import 'comprovante_card.dart';

class FaturaBottomSheet extends ConsumerStatefulWidget {
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
  ConsumerState<FaturaBottomSheet> createState() => _FaturaBottomSheetState();
}

class _FaturaBottomSheetState extends ConsumerState<FaturaBottomSheet> {
  String? _pixCodigo;
  bool _loadingPix = false;
  String? _pixError;

  @override
  void initState() {
    super.initState();
    if (widget.fatura.temPix) _loadPix();
  }

  Future<void> _loadPix() async {
    setState(() {
      _loadingPix = true;
      _pixError = null;
    });
    try {
      final codigo = await ref
          .read(faturasRepositoryProvider)
          .getPix(widget.fatura.id);
      if (!mounted) return;
      setState(() {
        _pixCodigo = codigo;
        _loadingPix = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _pixError = 'Não consegui gerar o PIX agora.';
        _loadingPix = false;
      });
    }
  }

  Future<void> _copyPix() async {
    final c = _pixCodigo;
    if (c == null) return;
    await Clipboard.setData(ClipboardData(text: c));
    await Haptics.success();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Código PIX copiado')),
    );
  }

  Future<void> _sharePix() async {
    final c = _pixCodigo;
    if (c == null) return;
    final fmtValor = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
    final fmtData = DateFormat('dd/MM/yyyy', 'pt_BR');
    final msg = 'Código Pix Ondeline\n\n'
        'Valor: ${fmtValor.format(widget.fatura.valor)}\n'
        'Vencimento: ${fmtData.format(widget.fatura.vencimentoDate)}\n\n'
        '$c';
    await Haptics.medium();
    await Share.share(msg, subject: 'Pix Ondeline');
  }

  Future<void> _shareBoleto() async {
    try {
      final url = await ref
          .read(faturasRepositoryProvider)
          .getBoletoUrl(widget.fatura.id);
      final fmtValor = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
      final fmtData = DateFormat('dd/MM/yyyy', 'pt_BR');
      final msg = 'Boleto Ondeline\n\n'
          'Valor: ${fmtValor.format(widget.fatura.valor)}\n'
          'Vencimento: ${fmtData.format(widget.fatura.vencimentoDate)}\n\n'
          '$url';
      await Haptics.medium();
      await Share.share(msg, subject: 'Boleto Ondeline');
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Falha ao gerar link do boleto')),
      );
    }
  }

  Future<void> _shareComprovante() async {
    final f = widget.fatura;
    final messenger = ScaffoldMessenger.of(context);
    messenger.showSnackBar(
      const SnackBar(
        duration: Duration(seconds: 2),
        content: Text('Gerando comprovante…'),
      ),
    );
    try {
      // Nome do cliente vem do meProvider — best-effort, fallback genérico.
      String nome = 'Cliente Ondeline';
      try {
        final me = await ref.read(meProvider.future);
        if (me.nome.trim().isNotEmpty) {
          nome = me.nome.trim();
        }
      } on Object {
        // ignore — usa fallback
      }

      final bytes = await renderWidgetToPng(
        ComprovanteCard(
          nomeCliente: nome,
          valor: f.valor,
          vencimento: f.vencimentoDate,
          faturaId: f.id,
          geradoEm: DateTime.now(),
        ),
        logicalSize: ComprovanteCard.designSize,
      );
      final tmp = await getTemporaryDirectory();
      final file = File(
        '${tmp.path}/comprovante_${f.id.replaceAll('-', '').substring(0, 8)}.png',
      );
      await file.writeAsBytes(bytes, flush: true);
      await Haptics.success();
      final fmtValor = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
      await Share.shareXFiles(
        [XFile(file.path, mimeType: 'image/png')],
        text:
            'Comprovante de pagamento — ${fmtValor.format(f.valor)} (Ondeline)',
        subject: 'Comprovante Ondeline',
      );
    } on Object catch (e) {
      messenger.showSnackBar(
        SnackBar(content: Text('Não consegui gerar o comprovante: $e')),
      );
    }
  }

  Future<void> _openBoleto() async {
    try {
      final url = await ref
          .read(faturasRepositoryProvider)
          .getBoletoUrl(widget.fatura.id);
      final ok = await launchUrl(
        Uri.parse(url),
        mode: LaunchMode.externalApplication,
      );
      if (!ok && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Não consegui abrir o boleto')),
        );
      }
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Falha ao abrir boleto')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final f = widget.fatura;
    final fmtValor = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
    final fmtData = DateFormat('dd/MM/yyyy', 'pt_BR');
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(
          BrandTokens.spaceLg,
          BrandTokens.spaceSm,
          BrandTokens.spaceLg,
          BrandTokens.spaceLg,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Handle
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

            // Valor + vencimento
            Text(
              fmtValor.format(f.valor),
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.displaySmall?.copyWith(
                    fontWeight: FontWeight.w900,
                    letterSpacing: -1,
                  ),
            ),
            const SizedBox(height: 4),
            Center(
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: BrandTokens.spaceMd,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: _statusColor(f).withOpacity(0.12),
                  borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
                ),
                child: Text(
                  '${_statusLabel(f)} · vence ${fmtData.format(f.vencimentoDate)}',
                  style: TextStyle(
                    color: _statusColor(f),
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                  ),
                ),
              ),
            ),
            const SizedBox(height: BrandTokens.spaceXl),

            // QR Pix
            if (f.temPix && f.isAberto) ...[
              if (_loadingPix)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: BrandTokens.spaceXl),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_pixError != null)
                Container(
                  padding: const EdgeInsets.all(BrandTokens.spaceMd),
                  decoration: BoxDecoration(
                    color: BrandTokens.danger.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
                    border: Border.all(
                      color: BrandTokens.danger.withOpacity(0.25),
                    ),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline,
                          color: BrandTokens.danger),
                      const SizedBox(width: BrandTokens.spaceSm),
                      Expanded(child: Text(_pixError!)),
                      TextButton(
                        onPressed: _loadPix,
                        child: const Text('Tentar de novo'),
                      ),
                    ],
                  ),
                )
              else if (_pixCodigo != null) ...[
                Center(
                  child: Container(
                    padding: const EdgeInsets.all(BrandTokens.spaceMd),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius:
                          BorderRadius.circular(BrandTokens.radiusLg),
                      boxShadow: BrandTokens.elevation1,
                    ),
                    child: QrImageView(
                      data: _pixCodigo!,
                      version: QrVersions.auto,
                      size: 220,
                      backgroundColor: Colors.white,
                      eyeStyle: const QrEyeStyle(
                        eyeShape: QrEyeShape.square,
                        color: BrandTokens.primaryDark,
                      ),
                      dataModuleStyle: const QrDataModuleStyle(
                        dataModuleShape: QrDataModuleShape.square,
                        color: BrandTokens.primaryDark,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: BrandTokens.spaceMd),
                Text(
                  'Aponte a câmera do seu app do banco',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: BrandTokens.textSecondary,
                      ),
                ),
                const SizedBox(height: BrandTokens.spaceLg),
                SizedBox(
                  height: 60,
                  child: FilledButton.icon(
                    icon: const Icon(Icons.copy_rounded, size: 22),
                    label: const Text(
                      'Copiar código Pix',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    onPressed: _copyPix,
                    style: FilledButton.styleFrom(
                      backgroundColor: BrandTokens.primary,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
                const SizedBox(height: BrandTokens.spaceSm),
                TextButton.icon(
                  icon: const Icon(Icons.share_rounded, size: 18),
                  label: const Text('Compartilhar Pix'),
                  onPressed: _sharePix,
                  style: TextButton.styleFrom(
                    minimumSize: const Size.fromHeight(44),
                  ),
                ),
              ],
              const SizedBox(height: BrandTokens.spaceSm),
            ],

            if (f.temPdf) ...[
              OutlinedButton.icon(
                icon: const Icon(Icons.picture_as_pdf_outlined),
                label: const Text('Abrir boleto em PDF'),
                onPressed: _openBoleto,
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size.fromHeight(52),
                  side: BorderSide(
                    color: isDark ? Colors.white24 : BrandTokens.divider,
                  ),
                ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              TextButton.icon(
                icon: const Icon(Icons.share_rounded, size: 18),
                label: const Text('Compartilhar boleto'),
                onPressed: _shareBoleto,
                style: TextButton.styleFrom(
                  minimumSize: const Size.fromHeight(44),
                ),
              ),
            ],

            // Faturas pagas: selo + botao "Compartilhar comprovante" (PNG)
            if (!f.isAberto) ...[
              const SizedBox(height: BrandTokens.spaceSm),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: BrandTokens.spaceMd,
                  vertical: BrandTokens.spaceMd,
                ),
                decoration: BoxDecoration(
                  color: BrandTokens.success.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
                  border: Border.all(
                    color: BrandTokens.success.withOpacity(0.30),
                  ),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.check_circle_rounded,
                      color: BrandTokens.success,
                    ),
                    const SizedBox(width: BrandTokens.spaceSm),
                    Expanded(
                      child: Text(
                        'Fatura paga',
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  color: BrandTokens.success,
                                  fontWeight: FontWeight.w800,
                                ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              SizedBox(
                height: 56,
                child: FilledButton.icon(
                  icon: const Icon(Icons.receipt_long_rounded),
                  label: const Text(
                    'Compartilhar comprovante',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  onPressed: _shareComprovante,
                  style: FilledButton.styleFrom(
                    backgroundColor: BrandTokens.success,
                    foregroundColor: Colors.white,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Color _statusColor(FaturaDto f) {
    if (f.status == 'pago') return BrandTokens.success;
    if (f.isVencido) return BrandTokens.danger;
    if (f.isAberto) return BrandTokens.warning;
    return BrandTokens.textSecondary;
  }

  String _statusLabel(FaturaDto f) {
    if (f.status == 'pago') return 'Paga';
    if (f.isVencido) return 'Vencida (${f.diasAtraso}d)';
    if (f.isAberto) return 'Em aberto';
    return f.status;
  }
}
