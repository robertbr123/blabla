import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/os_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/haptics.dart';

/// Bottom sheet de pesquisa NPS após OS concluída.
/// Cliente escolhe nota 0–10 (com cores detrator/passivo/promotor)
/// e opcionalmente deixa comentário.
Future<void> showNpsBottomSheet(
  BuildContext context, {
  required String osId,
  String? tipoLabel,
  String? numero,
  bool teveVisitaTecnica = false,
}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (_) => _NpsSheet(
      osId: osId,
      tipoLabel: tipoLabel,
      numero: numero,
      teveVisitaTecnica: teveVisitaTecnica,
    ),
  );
}

class _NpsSheet extends ConsumerStatefulWidget {
  const _NpsSheet({
    required this.osId,
    this.tipoLabel,
    this.numero,
    required this.teveVisitaTecnica,
  });
  final String osId;
  final String? tipoLabel;
  final String? numero;
  final bool teveVisitaTecnica;

  @override
  ConsumerState<_NpsSheet> createState() => _NpsSheetState();
}

class _NpsSheetState extends ConsumerState<_NpsSheet> {
  int? _score;
  final _comentarioCtrl = TextEditingController();
  bool _sending = false;
  bool? _pontual;
  bool? _educado;
  bool? _limpou;

  @override
  void dispose() {
    _comentarioCtrl.dispose();
    super.dispose();
  }

  Color _corDaNota(int n) {
    if (n <= 6) return BrandTokens.danger;
    if (n <= 8) return BrandTokens.warning;
    return BrandTokens.success;
  }

  String _labelDaNota(int? n) {
    if (n == null) return 'Toque numa nota';
    if (n <= 6) return 'Que pena! Vamos melhorar.';
    if (n <= 8) return 'Bom. Dá pra melhorar.';
    return 'Que ótimo, valeu!';
  }

  Future<void> _enviar() async {
    if (_score == null) return;
    setState(() => _sending = true);
    try {
      await ref.read(osRepositoryProvider).submeterNps(
            osId: widget.osId,
            score: _score!,
            comentario: _comentarioCtrl.text.trim(),
            tecnicoPontual: widget.teveVisitaTecnica ? _pontual : null,
            tecnicoEducado: widget.teveVisitaTecnica ? _educado : null,
            tecnicoLimpou: widget.teveVisitaTecnica ? _limpou : null,
          );
      if (!mounted) return;
      await Haptics.success();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Obrigado pela sua avaliação!')),
      );
      Navigator.of(context).pop();
    } on Object catch (_) {
      if (!mounted) return;
      await Haptics.error();
      setState(() => _sending = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Não consegui enviar. Tente novamente.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final media = MediaQuery.of(context);
    return Padding(
      padding: EdgeInsets.only(bottom: media.viewInsets.bottom),
      child: Container(
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(BrandTokens.radiusXl),
          ),
        ),
        padding: const EdgeInsets.fromLTRB(
          BrandTokens.spaceLg,
          BrandTokens.spaceMd,
          BrandTokens.spaceLg,
          BrandTokens.spaceLg,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: BrandTokens.spaceLg),
            const Text(
              'Como foi seu atendimento?',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w800,
                color: BrandTokens.primaryDark,
                letterSpacing: -0.3,
              ),
            ),
            if (widget.tipoLabel != null || widget.numero != null) ...[
              const SizedBox(height: BrandTokens.spaceXs),
              _ReferenciaChamado(
                tipoLabel: widget.tipoLabel,
                numero: widget.numero,
              ),
            ],
            const SizedBox(height: BrandTokens.spaceXs),
            const Text(
              'De 0 a 10, qual a chance de você indicar nosso atendimento?',
              style: TextStyle(
                fontSize: 14,
                color: Colors.black54,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: BrandTokens.spaceLg),
            Wrap(
              spacing: BrandTokens.spaceSm,
              runSpacing: BrandTokens.spaceSm,
              alignment: WrapAlignment.center,
              children: List.generate(11, (n) {
                final selecionado = _score == n;
                final cor = _corDaNota(n);
                return GestureDetector(
                  onTap: _sending
                      ? null
                      : () {
                          Haptics.light();
                          setState(() => _score = n);
                        },
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    width: 44,
                    height: 44,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: selecionado ? cor : Colors.white,
                      borderRadius:
                          BorderRadius.circular(BrandTokens.radiusSm),
                      border: Border.all(
                        color: selecionado ? cor : Colors.black12,
                        width: selecionado ? 0 : 1,
                      ),
                      boxShadow: selecionado
                          ? [
                              BoxShadow(
                                color: cor.withOpacity(0.35),
                                blurRadius: 12,
                                offset: const Offset(0, 4),
                              ),
                            ]
                          : null,
                    ),
                    child: Text(
                      '$n',
                      style: TextStyle(
                        color: selecionado ? Colors.white : Colors.black87,
                        fontWeight: FontWeight.w800,
                        fontSize: 16,
                      ),
                    ),
                  ),
                );
              }),
            ),
            const SizedBox(height: BrandTokens.spaceMd),
            Center(
              child: Text(
                _labelDaNota(_score),
                style: TextStyle(
                  color: _score == null
                      ? Colors.black45
                      : _corDaNota(_score!),
                  fontWeight: FontWeight.w700,
                  fontSize: 14,
                ),
              ),
            ),
            const SizedBox(height: BrandTokens.spaceLg),
            TextField(
              controller: _comentarioCtrl,
              enabled: !_sending,
              minLines: 2,
              maxLines: 4,
              maxLength: 2000,
              decoration: InputDecoration(
                hintText: 'Quer deixar um comentário? (opcional)',
                filled: true,
                fillColor: Colors.black.withOpacity(0.04),
                border: OutlineInputBorder(
                  borderRadius:
                      BorderRadius.circular(BrandTokens.radiusMd),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
            if (widget.teveVisitaTecnica) ...[
              const SizedBox(height: BrandTokens.spaceMd),
              const Divider(),
              const SizedBox(height: BrandTokens.spaceMd),
              const Text(
                'Sobre a visita técnica',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                  color: BrandTokens.primaryDark,
                ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              _AvaliacaoBin(
                label: 'O técnico chegou no horário?',
                valor: _pontual,
                onChange: _sending
                    ? null
                    : (v) => setState(() => _pontual = v),
              ),
              _AvaliacaoBin(
                label: 'Foi educado e atencioso?',
                valor: _educado,
                onChange: _sending
                    ? null
                    : (v) => setState(() => _educado = v),
              ),
              _AvaliacaoBin(
                label: 'Deixou o local limpo após o serviço?',
                valor: _limpou,
                onChange: _sending
                    ? null
                    : (v) => setState(() => _limpou = v),
              ),
            ],
            const SizedBox(height: BrandTokens.spaceSm),
            SizedBox(
              height: 52,
              child: FilledButton(
                onPressed:
                    (_score == null || _sending) ? null : _enviar,
                style: FilledButton.styleFrom(
                  backgroundColor: BrandTokens.primary,
                  disabledBackgroundColor:
                      BrandTokens.primary.withOpacity(0.4),
                  shape: RoundedRectangleBorder(
                    borderRadius:
                        BorderRadius.circular(BrandTokens.radiusMd),
                  ),
                ),
                child: _sending
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            Colors.white,
                          ),
                        ),
                      )
                    : const Text(
                        'Enviar avaliação',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                        ),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AvaliacaoBin extends StatelessWidget {
  const _AvaliacaoBin({
    required this.label,
    required this.valor,
    required this.onChange,
  });
  final String label;
  final bool? valor;
  final ValueChanged<bool?>? onChange;

  Widget _btn(BuildContext context, {required bool value, required String txt}) {
    final selected = valor == value;
    final cor = value ? BrandTokens.success : BrandTokens.danger;
    return GestureDetector(
      onTap: onChange == null
          ? null
          : () => onChange!(selected ? null : value),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 140),
        padding: const EdgeInsets.symmetric(
          horizontal: BrandTokens.spaceMd,
          vertical: 8,
        ),
        decoration: BoxDecoration(
          color: selected ? cor : Colors.white,
          borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
          border: Border.all(
            color: selected ? cor : Colors.black12,
            width: selected ? 0 : 1,
          ),
        ),
        child: Text(
          txt,
          style: TextStyle(
            color: selected ? Colors.white : Colors.black87,
            fontWeight: FontWeight.w700,
            fontSize: 13,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(
                color: BrandTokens.primaryDark,
                fontSize: 13.5,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          const SizedBox(width: BrandTokens.spaceSm),
          _btn(context, value: true, txt: 'Sim'),
          const SizedBox(width: 6),
          _btn(context, value: false, txt: 'Não'),
        ],
      ),
    );
  }
}

class _ReferenciaChamado extends StatelessWidget {
  const _ReferenciaChamado({this.tipoLabel, this.numero});
  final String? tipoLabel;
  final String? numero;

  @override
  Widget build(BuildContext context) {
    final partes = <String>[];
    if (numero != null && numero!.isNotEmpty) partes.add('Chamado #$numero');
    if (tipoLabel != null && tipoLabel!.isNotEmpty) partes.add(tipoLabel!);
    if (partes.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(top: BrandTokens.spaceXs),
      padding: const EdgeInsets.symmetric(
        horizontal: BrandTokens.spaceSm + 2,
        vertical: 6,
      ),
      decoration: BoxDecoration(
        color: BrandTokens.primary.withOpacity(0.10),
        borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
      ),
      child: Text(
        partes.join(' — '),
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(
          color: BrandTokens.primary,
          fontWeight: FontWeight.w700,
          fontSize: 12.5,
        ),
      ),
    );
  }
}
