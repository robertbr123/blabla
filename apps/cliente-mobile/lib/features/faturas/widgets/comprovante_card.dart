import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../core/branding/brand_tokens.dart';

/// Comprovante visual de pagamento — usado pra gerar PNG compartilhavel.
///
/// Tamanho fixo: 540x800 (proporcao 4.7:6.96 — cabe bem em status do
/// WhatsApp em retrato e fica legivel em chat). Renderizado offscreen
/// via [renderWidgetToPng].
class ComprovanteCard extends StatelessWidget {
  const ComprovanteCard({
    super.key,
    required this.nomeCliente,
    required this.valor,
    required this.vencimento,
    required this.faturaId,
    required this.geradoEm,
    this.nomeEmpresa = 'Ondeline',
  });

  final String nomeCliente;
  final double valor;
  final DateTime vencimento;
  final String faturaId;
  final DateTime geradoEm;
  final String nomeEmpresa;

  static const Size designSize = Size(540, 800);

  String _idCurto(String id) {
    final clean = id.replaceAll('-', '');
    return clean.length <= 8
        ? clean.toUpperCase()
        : clean.substring(0, 8).toUpperCase();
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
        decoration: const BoxDecoration(
          color: Color(0xFFF4F8FA),
        ),
        padding: const EdgeInsets.all(28),
        child: Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(28),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.06),
                blurRadius: 24,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Column(
            children: [
              // Header com gradient
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(24),
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Color(0xFF0B1F3A),
                      Color(0xFF14B8B0),
                    ],
                  ),
                  borderRadius: BorderRadius.only(
                    topLeft: Radius.circular(28),
                    topRight: Radius.circular(28),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 32,
                          height: 32,
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          alignment: Alignment.center,
                          child: const Text(
                            'O',
                            style: TextStyle(
                              fontWeight: FontWeight.w900,
                              color: BrandTokens.primaryDark,
                              fontSize: 18,
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Text(
                          nomeEmpresa,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w800,
                            fontSize: 18,
                          ),
                        ),
                        const Spacer(),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 5,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(0xFF14B8B0),
                            borderRadius: BorderRadius.circular(999),
                            border:
                                Border.all(color: Colors.white, width: 1.5),
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
                                  fontSize: 12,
                                  letterSpacing: 1,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    const Text(
                      'Comprovante de pagamento',
                      style: TextStyle(
                        color: Colors.white70,
                        fontWeight: FontWeight.w700,
                        fontSize: 13,
                        letterSpacing: 0.5,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      fmtValor.format(valor),
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                        fontSize: 44,
                        letterSpacing: -1,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              // Body
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _Row(label: 'Cliente', value: nomeCliente),
                    const SizedBox(height: 14),
                    _Row(
                      label: 'Vencimento',
                      value: fmtData.format(vencimento),
                    ),
                    const SizedBox(height: 14),
                    _Row(
                      label: 'Identificador',
                      value: '#${_idCurto(faturaId)}',
                    ),
                    const SizedBox(height: 24),
                    Container(
                      height: 1,
                      color: BrandTokens.divider,
                    ),
                    const SizedBox(height: 20),
                    Text(
                      'Gerado em ${fmtDataHora.format(geradoEm)}',
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: BrandTokens.textSecondary,
                        fontWeight: FontWeight.w600,
                        fontSize: 12,
                      ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Para conferência, fale com o suporte com o identificador acima.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: BrandTokens.textSecondary,
                        fontSize: 11,
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
              const Spacer(),
              // Footer
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 14),
                decoration: const BoxDecoration(
                  color: Color(0xFFF4F8FA),
                  borderRadius: BorderRadius.only(
                    bottomLeft: Radius.circular(28),
                    bottomRight: Radius.circular(28),
                  ),
                ),
                child: const Text(
                  'Documento informativo — não tem valor fiscal.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: BrandTokens.textSecondary,
                    fontWeight: FontWeight.w700,
                    fontSize: 11,
                    letterSpacing: 0.3,
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

class _Row extends StatelessWidget {
  const _Row({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 110,
          child: Text(
            label,
            style: const TextStyle(
              color: BrandTokens.textSecondary,
              fontWeight: FontWeight.w700,
              fontSize: 13,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(
              color: BrandTokens.primaryDark,
              fontWeight: FontWeight.w800,
              fontSize: 15,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}
