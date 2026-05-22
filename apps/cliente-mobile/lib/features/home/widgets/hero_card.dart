import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/api/dto.dart';
import '../../../core/api/faturas_repository.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../shell/main_shell.dart';
import 'connection_status_pill.dart';

/// Hero da Home — padrao dos cards do Perfil/Faturas (surface, sombra leve)
/// com informacao acionavel: linha de cima identifica o cliente + status do
/// servico; linha de baixo mostra a fatura em aberto mais urgente (se houver)
/// ou estado "em dia".
class HeroCard extends ConsumerWidget {
  const HeroCard({super.key, required this.me});
  final MeDto me;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final faturasAsync = ref.watch(faturasAbertasProvider);
    final fatura = faturasAsync.maybeWhen(
      data: (l) => l.isEmpty ? null : l.first,
      orElse: () => null,
    );

    return Container(
      decoration: BoxDecoration(
        color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(
          color: isDark ? Colors.white12 : BrandTokens.divider,
        ),
        boxShadow: BrandTokens.elevation1,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Linha 1: avatar + nome/plano + status pill
          Padding(
            padding: const EdgeInsets.all(BrandTokens.spaceMd),
            child: Row(
              children: [
                _Avatar(nome: me.nome),
                const SizedBox(width: BrandTokens.spaceMd),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        _saudacaoComNome(me.nome),
                        style: const TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 15,
                          letterSpacing: -0.2,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Row(
                        children: [
                          const Icon(
                            Icons.wifi_rounded,
                            size: 13,
                            color: BrandTokens.primary,
                          ),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              me.planoNome ?? 'Sem plano vinculado',
                              style: const TextStyle(
                                color: BrandTokens.textSecondary,
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: BrandTokens.spaceSm),
                const ConnectionStatusPill(),
              ],
            ),
          ),

          // Linha 2: footer com fatura ou "em dia"
          _FaturaFooter(fatura: fatura, ref: ref),
        ],
      ),
    );
  }

  String _saudacaoComNome(String full) {
    final hora = DateTime.now().hour;
    final cumprimento = hora < 12
        ? 'Bom dia'
        : hora < 18
            ? 'Boa tarde'
            : 'Boa noite';
    final t = full.trim();
    final nome = t.isEmpty ? 'Cliente' : t.split(' ').first;
    return '$cumprimento, $nome';
  }
}

class _Avatar extends StatelessWidget {
  const _Avatar({required this.nome});
  final String nome;

  String _iniciais() {
    final t = nome.trim();
    if (t.isEmpty) return '?';
    final parts = t.split(RegExp(r'\s+')).where((s) => s.isNotEmpty).toList();
    if (parts.length == 1) return parts[0][0].toUpperCase();
    return (parts.first[0] + parts.last[0]).toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: BrandTokens.gradientHero,
        boxShadow: BrandTokens.shadowColored,
      ),
      alignment: Alignment.center,
      child: Text(
        _iniciais(),
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w900,
          fontSize: 16,
          letterSpacing: 0.4,
        ),
      ),
    );
  }
}

/// Footer dinamico — fatura urgente, vencida, ou "em dia".
class _FaturaFooter extends StatelessWidget {
  const _FaturaFooter({required this.fatura, required this.ref});
  final FaturaDto? fatura;
  final WidgetRef ref;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final divider = isDark ? Colors.white10 : BrandTokens.divider;

    final (color, icon, titulo, valor) = _content();

    return InkWell(
      onTap: () => ref.read(mainShellTabProvider.notifier).state = 1,
      borderRadius: const BorderRadius.only(
        bottomLeft: Radius.circular(BrandTokens.radiusLg),
        bottomRight: Radius.circular(BrandTokens.radiusLg),
      ),
      child: Container(
        decoration: BoxDecoration(
          color: color.withOpacity(0.06),
          border: Border(
            top: BorderSide(color: divider),
          ),
          borderRadius: const BorderRadius.only(
            bottomLeft: Radius.circular(BrandTokens.radiusLg),
            bottomRight: Radius.circular(BrandTokens.radiusLg),
          ),
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: BrandTokens.spaceMd,
          vertical: 10,
        ),
        child: Row(
          children: [
            Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                color: color.withOpacity(0.16),
                borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
              ),
              child: Icon(icon, color: color, size: 16),
            ),
            const SizedBox(width: BrandTokens.spaceSm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    titulo,
                    style: TextStyle(
                      color: color,
                      fontWeight: FontWeight.w800,
                      fontSize: 12.5,
                    ),
                  ),
                  if (valor != null)
                    Text(
                      valor,
                      style: const TextStyle(
                        color: BrandTokens.textSecondary,
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right_rounded,
              color: color,
              size: 18,
            ),
          ],
        ),
      ),
    );
  }

  (Color, IconData, String, String?) _content() {
    final f = fatura;
    if (f == null) {
      return (
        BrandTokens.success,
        Icons.check_circle_rounded,
        'Você esta em dia',
        'Nenhuma fatura em aberto',
      );
    }
    final fmtV = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
    final fmtD = DateFormat('dd/MM', 'pt_BR');
    final hoje = DateTime.now();
    final venc = f.vencimentoDate;
    final dias = DateTime(venc.year, venc.month, venc.day)
        .difference(DateTime(hoje.year, hoje.month, hoje.day))
        .inDays;

    if (f.isVencido) {
      return (
        BrandTokens.danger,
        Icons.warning_amber_rounded,
        'Fatura vencida ha ${f.diasAtraso} dia${f.diasAtraso == 1 ? '' : 's'}',
        '${fmtV.format(f.valor)} · vencimento ${fmtD.format(venc)}',
      );
    }
    if (dias == 0) {
      return (
        BrandTokens.warning,
        Icons.today_rounded,
        'Fatura vence hoje',
        fmtV.format(f.valor),
      );
    }
    if (dias <= 3) {
      return (
        BrandTokens.warning,
        Icons.schedule_rounded,
        'Fatura vence em $dias dia${dias == 1 ? '' : 's'}',
        '${fmtV.format(f.valor)} · ${fmtD.format(venc)}',
      );
    }
    return (
      BrandTokens.info,
      Icons.receipt_long_rounded,
      'Próxima fatura em $dias dias',
      '${fmtV.format(f.valor)} · vencimento ${fmtD.format(venc)}',
    );
  }
}
