import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../core/branding/brand_tokens.dart';

/// Comprovante premium — usado pra gerar PNG compartilhavel.
///
/// Renderizado offscreen via [renderWidgetToPng]. Tamanho fixo 600x980
/// (proporcao ~3:5) — fica bem em status do WhatsApp e enxerga legivel
/// em chat.
class ComprovanteCard extends StatelessWidget {
  const ComprovanteCard({
    super.key,
    required this.nomeCliente,
    required this.valor,
    required this.vencimento,
    required this.faturaId,
    required this.geradoEm,
    this.logoImage,
    this.nomeEmpresa = 'Ondeline',
  });

  final String nomeCliente;
  final double valor;
  final DateTime vencimento;
  final String faturaId;
  final DateTime geradoEm;
  /// Logo pre-decodificada (necessario pra render offscreen funcionar).
  /// Quando null, mostra um placeholder com a letra 'O'.
  final ui.Image? logoImage;
  final String nomeEmpresa;

  static const Size designSize = Size(600, 980);

  static const Color _gold = BrandTokens.warning;
  static const Color _navy = BrandTokens.primaryDark;
  static const Color _teal = BrandTokens.primary;

  String _idCurto(String id) {
    final clean = id.replaceAll('-', '').toUpperCase();
    if (clean.length <= 10) return clean;
    return clean.substring(0, 10);
  }

  @override
  Widget build(BuildContext context) {
    final fmtValor = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
    final fmtData = DateFormat('dd/MM/yyyy', 'pt_BR');
    final fmtDataHora = DateFormat('dd/MM/yyyy HH:mm', 'pt_BR');

    return SizedBox(
      width: designSize.width,
      height: designSize.height,
      child: Container(
        // Backdrop escuro pra dar profundidade premium
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [BrandTokens.backgroundDark, BrandTokens.primaryDark],
          ),
        ),
        padding: const EdgeInsets.all(32),
        child: Stack(
          children: [
            // Padrao de pontos decorativo no fundo
            Positioned.fill(
              child: CustomPaint(painter: _DotsPainter()),
            ),
            // Card branco com entalhes laterais (notch perto da base, antes do footer)
            ClipPath(
              clipper: const _TicketClipper(notchYRatio: 0.86, notchRadius: 14),
              child: Container(
                color: Colors.white,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _Header(
                      nomeEmpresa: nomeEmpresa,
                      valor: valor,
                      fmtValor: fmtValor,
                      logoImage: logoImage,
                    ),
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(32, 28, 32, 16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            const Text(
                              'BENEFICIÁRIO',
                              style: TextStyle(
                                color: BrandTokens.textSecondary,
                                fontSize: 11,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 2,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              nomeCliente,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: _navy,
                                fontSize: 22,
                                fontWeight: FontWeight.w900,
                                letterSpacing: -0.4,
                                height: 1.15,
                              ),
                            ),
                            const SizedBox(height: 24),
                            Row(
                              children: [
                                Expanded(
                                  child: _InfoBlock(
                                    label: 'VENCIMENTO',
                                    value: fmtData.format(vencimento),
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: _InfoBlock(
                                    label: 'PAGO EM',
                                    value: fmtData.format(geradoEm),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 24),
                            const Text(
                              'IDENTIFICADOR',
                              style: TextStyle(
                                color: BrandTokens.textSecondary,
                                fontSize: 10,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 2,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 14,
                                vertical: 12,
                              ),
                              decoration: BoxDecoration(
                                color: BrandTokens.background,
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(
                                  color: BrandTokens.divider,
                                ),
                              ),
                              child: Row(
                                children: [
                                  const Icon(
                                    Icons.qr_code_2_rounded,
                                    color: _navy,
                                    size: 26,
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Text(
                                      '#${_idCurto(faturaId)}',
                                      style: const TextStyle(
                                        color: _navy,
                                        fontSize: 18,
                                        fontWeight: FontWeight.w900,
                                        fontFamily: 'monospace',
                                        letterSpacing: 1.5,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const Spacer(),
                            const _DashedDivider(),
                            const SizedBox(height: 12),
                            Text(
                              'Gerado em ${fmtDataHora.format(geradoEm)}.\nPasse o identificador pro suporte se precisar validar.',
                              textAlign: TextAlign.center,
                              style: const TextStyle(
                                color: BrandTokens.textSecondary,
                                fontSize: 10.5,
                                height: 1.45,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    // Footer "marca registrada"
                    Container(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      decoration: const BoxDecoration(
                        gradient: LinearGradient(
                          colors: [_navy, _teal],
                          begin: Alignment.centerLeft,
                          end: Alignment.centerRight,
                        ),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(
                            Icons.verified_rounded,
                            color: _gold,
                            size: 14,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            '$nomeEmpresa  ·  Documento informativo',
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w800,
                              fontSize: 11,
                              letterSpacing: 1,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            // Watermark "PAGO" gigante de fundo (rotacionado, baixa opacidade)
            const Positioned.fill(child: _WatermarkPago()),
          ],
        ),
      ),
    );
  }
}

// ────────────────────── Header (logo + selo + valor) ──────────────────────

class _Header extends StatelessWidget {
  const _Header({
    required this.nomeEmpresa,
    required this.valor,
    required this.fmtValor,
    required this.logoImage,
  });
  final String nomeEmpresa;
  final double valor;
  final NumberFormat fmtValor;
  final ui.Image? logoImage;

  static const Color _gold = BrandTokens.warning;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(32, 32, 32, 32),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            BrandTokens.primaryDark,
            Color(0xFF134A6F), // tom intermediário do gradiente, exclusivo deste card
            BrandTokens.primary,
          ],
          stops: [0.0, 0.55, 1.0],
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Logo + nome + selo
          Row(
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.18),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                clipBehavior: Clip.antiAlias,
                child: logoImage != null
                    ? RawImage(image: logoImage, fit: BoxFit.cover)
                    : Container(
                        color: BrandTokens.primaryDark,
                        alignment: Alignment.center,
                        child: const Text(
                          'O',
                          style: TextStyle(
                            color: BrandTokens.primary,
                            fontWeight: FontWeight.w900,
                            fontSize: 28,
                          ),
                        ),
                      ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      nomeEmpresa,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                        fontSize: 20,
                        letterSpacing: -0.3,
                      ),
                    ),
                    const Text(
                      'COMPROVANTE DE PAGAMENTO',
                      style: TextStyle(
                        color: Colors.white60,
                        fontWeight: FontWeight.w800,
                        fontSize: 9.5,
                        letterSpacing: 1.8,
                      ),
                    ),
                  ],
                ),
              ),
              // Selo PAGA gold
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: _gold,
                  borderRadius: BorderRadius.circular(999),
                  boxShadow: [
                    BoxShadow(
                      color: _gold.withOpacity(0.4),
                      blurRadius: 10,
                      offset: const Offset(0, 3),
                    ),
                  ],
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.check_circle_rounded,
                      color: Colors.white,
                      size: 14,
                    ),
                    SizedBox(width: 4),
                    Text(
                      'PAGA',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                        fontSize: 11,
                        letterSpacing: 1.5,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 36),
          const Text(
            'VALOR PAGO',
            style: TextStyle(
              color: Colors.white60,
              fontWeight: FontWeight.w800,
              fontSize: 11,
              letterSpacing: 2,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            fmtValor.format(valor),
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w900,
              fontSize: 52,
              letterSpacing: -2,
              height: 1.05,
            ),
          ),
        ],
      ),
    );
  }
}

// ────────────────────── Bloco de info (label + valor) ──────────────────────

class _InfoBlock extends StatelessWidget {
  const _InfoBlock({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: BrandTokens.background,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: BrandTokens.textSecondary,
              fontWeight: FontWeight.w800,
              fontSize: 10,
              letterSpacing: 1.5,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: const TextStyle(
              color: BrandTokens.primaryDark,
              fontWeight: FontWeight.w900,
              fontSize: 16,
            ),
          ),
        ],
      ),
    );
  }
}

// ────────────────────── Separador tracejado (linha do recorte) ──────────────────────

class _DashedDivider extends StatelessWidget {
  const _DashedDivider();

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 1,
      child: CustomPaint(
        painter: _DashedLinePainter(),
        size: const Size(double.infinity, 1),
      ),
    );
  }
}

class _DashedLinePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = BrandTokens.divider
      ..strokeWidth = 1;
    const dashWidth = 6.0;
    const dashSpace = 5.0;
    double startX = 0;
    while (startX < size.width) {
      canvas.drawLine(
        Offset(startX, 0),
        Offset(startX + dashWidth, 0),
        paint,
      );
      startX += dashWidth + dashSpace;
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

// ────────────────────── Padrao de pontos decorativo ──────────────────────

class _DotsPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = Colors.white.withOpacity(0.03);
    const spacing = 22.0;
    const radius = 1.2;
    for (double y = 0; y < size.height; y += spacing) {
      for (double x = 0; x < size.width; x += spacing) {
        canvas.drawCircle(Offset(x, y), radius, paint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

// ────────────────────── Watermark "PAGO" gigante rotacionado ──────────────────────

class _WatermarkPago extends StatelessWidget {
  const _WatermarkPago();

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Center(
        child: Transform.rotate(
          angle: -0.35,
          child: Text(
            'PAGO',
            style: TextStyle(
              color: BrandTokens.warning.withOpacity(0.06),
              fontSize: 200,
              fontWeight: FontWeight.w900,
              letterSpacing: -6,
            ),
          ),
        ),
      ),
    );
  }
}

// ────────────────────── Ticket clipper (entalhes laterais) ──────────────────────

/// Recorta o card branco com dois entalhes circulares laterais na altura
/// `notchY` — gera o efeito de bilhete/ticket com perfuracao.
class _TicketClipper extends CustomClipper<Path> {
  const _TicketClipper({
    required this.notchYRatio,
    required this.notchRadius,
  });
  final double notchYRatio;
  final double notchRadius;

  @override
  Path getClip(Size size) {
    const r = 24.0;
    final notchY = size.height * notchYRatio;
    final path = Path();

    path.moveTo(r, 0);
    path.lineTo(size.width - r, 0);
    path.quadraticBezierTo(size.width, 0, size.width, r);

    path.lineTo(size.width, notchY - notchRadius);
    path.arcToPoint(
      Offset(size.width, notchY + notchRadius),
      radius: Radius.circular(notchRadius),
      clockwise: false,
    );

    path.lineTo(size.width, size.height - r);
    path.quadraticBezierTo(
      size.width,
      size.height,
      size.width - r,
      size.height,
    );

    path.lineTo(r, size.height);
    path.quadraticBezierTo(0, size.height, 0, size.height - r);

    path.lineTo(0, notchY + notchRadius);
    path.arcToPoint(
      Offset(0, notchY - notchRadius),
      radius: Radius.circular(notchRadius),
      clockwise: false,
    );

    path.lineTo(0, r);
    path.quadraticBezierTo(0, 0, r, 0);

    path.close();
    return path;
  }

  @override
  bool shouldReclip(covariant CustomClipper<Path> oldClipper) => false;
}
