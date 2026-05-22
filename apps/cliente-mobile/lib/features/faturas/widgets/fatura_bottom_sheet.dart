import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/api/dto.dart';
import '../../../core/api/faturas_repository.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../../core/ui/haptics.dart';

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

            // Faturas pagas: so mostra resumo + boleto
            if (!f.isAberto && !f.temPdf)
              Padding(
                padding: const EdgeInsets.symmetric(
                  vertical: BrandTokens.spaceLg,
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(
                      Icons.check_circle,
                      color: BrandTokens.success,
                    ),
                    const SizedBox(width: BrandTokens.spaceSm),
                    Text(
                      'Fatura paga',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: BrandTokens.success,
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                  ],
                ),
              ),
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
