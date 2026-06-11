import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/fidelidade_repository.dart';
import '../../core/api/missoes_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/glass_app_bar.dart';
import '../../core/ui/haptics.dart';
import '../home/promo_icon_map.dart';

class FidelidadeScreen extends ConsumerWidget {
  const FidelidadeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(fidelidadeProvider);
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: GlassAppBar(title: 'Programa de fidelidade'),
      body: RefreshIndicator(
        edgeOffset: MediaQuery.paddingOf(context).top + kToolbarHeight,
        onRefresh: () async {
          ref.invalidate(fidelidadeProvider);
          ref.invalidate(missoesProvider);
          await ref.read(fidelidadeProvider.future);
        },
        child: async.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: EdgeInsets.only(
              top: MediaQuery.paddingOf(context).top + kToolbarHeight + BrandTokens.spaceMd,
            ),
            children: const [
              Icon(Icons.error_outline, size: 64, color: BrandTokens.danger),
              SizedBox(height: BrandTokens.spaceMd),
              Center(
                child: Text(
                  'Não conseguimos carregar agora.',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
            ],
          ),
          data: (data) => _Content(data: data),
        ),
      ),
    );
  }
}

class _Content extends ConsumerWidget {
  const _Content({required this.data});
  final FidelidadeDto data;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: EdgeInsets.fromLTRB(
        BrandTokens.spaceLg,
        MediaQuery.paddingOf(context).top + kToolbarHeight + BrandTokens.spaceMd,
        BrandTokens.spaceLg,
        BrandTokens.spaceLg,
      ),
      children: [
        _SaldoCard(data: data),
        const SizedBox(height: BrandTokens.spaceLg),
        const Text(
          'Como você ganhou',
          style: TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 14,
            color: BrandTokens.textSecondary,
          ),
        ),
        const SizedBox(height: BrandTokens.spaceSm),
        _BreakdownCard(b: data.breakdown),
        const SizedBox(height: BrandTokens.spaceLg),
        const _MissoesSection(),
        const Text(
          'Trocar pontos',
          style: TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 14,
            color: BrandTokens.textSecondary,
          ),
        ),
        const SizedBox(height: BrandTokens.spaceSm),
        for (final r in data.recompensas)
          _RecompensaCard(recompensa: r),
        if (data.resgates.isNotEmpty) ...[
          const SizedBox(height: BrandTokens.spaceLg),
          const Text(
            'Seus resgates',
            style: TextStyle(
              fontWeight: FontWeight.w800,
              fontSize: 14,
              color: BrandTokens.textSecondary,
            ),
          ),
          const SizedBox(height: BrandTokens.spaceSm),
          for (final r in data.resgates) _ResgateRow(r: r),
        ],
        const SizedBox(height: BrandTokens.spaceLg),
        const _RegrasInfo(),
      ],
    );
  }
}

class _SaldoCard extends StatelessWidget {
  const _SaldoCard({required this.data});
  final FidelidadeDto data;

  @override
  Widget build(BuildContext context) {
    final reservados = data.pontosTotal - data.pontosDisponiveis;
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        gradient: BrandTokens.gradientPrimary,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        boxShadow: BrandTokens.shadowColored,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Seus pontos',
            style: TextStyle(
              color: Colors.white70,
              fontSize: 13,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.3,
            ),
          ),
          const SizedBox(height: 4),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                '${data.pontosDisponiveis}',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 42,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -1.0,
                ),
              ),
              const SizedBox(width: 6),
              const Text(
                'pts',
                style: TextStyle(
                  color: Colors.white70,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          if (reservados > 0)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                '$reservados pts em resgates pendentes',
                style: const TextStyle(
                  color: Colors.white60,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          const SizedBox(height: BrandTokens.spaceXs),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: BrandTokens.spaceSm,
              vertical: 4,
            ),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.20),
              borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
            ),
            child: Text(
              'Total acumulado: ${data.pontosTotal} pts',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 11.5,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.3,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BreakdownCard extends StatelessWidget {
  const _BreakdownCard({required this.b});
  final FidelidadeBreakdownDto b;

  @override
  Widget build(BuildContext context) {
    final mesesTxt = b.tempoCasaMeses == 1
        ? '1 mês de Ondeline'
        : '${b.tempoCasaMeses} meses de Ondeline';
    final pagasTxt = b.faturasPagasQtd == 1
        ? '1 fatura paga'
        : '${b.faturasPagasQtd} faturas pagas';
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: BrandTokens.spaceMd,
        vertical: BrandTokens.spaceSm,
      ),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(color: BrandTokens.divider),
      ),
      child: Column(
        children: [
          _BreakdownRow(
            icon: Icons.home_rounded,
            label: mesesTxt,
            pontos: '+${b.tempoCasaPontos}',
          ),
          const Divider(height: 8),
          _BreakdownRow(
            icon: Icons.check_circle_outline_rounded,
            label: pagasTxt,
            pontos: '+${b.faturasPagasPontos}',
          ),
          if (b.missoesQtd > 0) ...[
            const Divider(height: 8),
            _BreakdownRow(
              icon: Icons.emoji_events_rounded,
              label: b.missoesQtd == 1
                  ? '1 missão concluída'
                  : '${b.missoesQtd} missões concluídas',
              pontos: '+${b.missoesPontos}',
            ),
          ],
        ],
      ),
    );
  }
}

class _MissoesSection extends ConsumerWidget {
  const _MissoesSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(missoesProvider);
    return async.maybeWhen(
      data: (items) {
        if (items.isEmpty) return const SizedBox.shrink();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Missões',
              style: TextStyle(
                fontWeight: FontWeight.w800,
                fontSize: 14,
                color: BrandTokens.textSecondary,
              ),
            ),
            const SizedBox(height: BrandTokens.spaceSm),
            for (final m in items) _MissaoCard(missao: m),
            const SizedBox(height: BrandTokens.spaceLg),
          ],
        );
      },
      orElse: () => const SizedBox.shrink(),
    );
  }
}

class _MissaoCard extends StatelessWidget {
  const _MissaoCard({required this.missao});
  final MissaoItemDto missao;

  ({String label, Color color, IconData icon}) get _statusMeta {
    if (missao.periodicidade == 'diaria') {
      if (missao.completadaHoje) {
        return (
          label: 'Feita hoje',
          color: BrandTokens.success,
          icon: Icons.check_circle_rounded,
        );
      }
      return (
        label: 'Disponível hoje',
        color: BrandTokens.primary,
        icon: Icons.bolt_rounded,
      );
    }
    // por_os e on_the_fly: sempre disponivel, mostra contagem.
    return (
      label: missao.totalConcluida == 0
          ? 'Comece já'
          : '${missao.totalConcluida}x feita',
      color: missao.totalConcluida == 0
          ? BrandTokens.primary
          : BrandTokens.success,
      icon: missao.totalConcluida == 0
          ? Icons.bolt_rounded
          : Icons.repeat_rounded,
    );
  }

  @override
  Widget build(BuildContext context) {
    final meta = _statusMeta;
    return Container(
      margin: const EdgeInsets.only(bottom: BrandTokens.spaceSm),
      padding: const EdgeInsets.all(BrandTokens.spaceMd),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(color: BrandTokens.divider),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: meta.color.withOpacity(0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            alignment: Alignment.center,
            child: Icon(promoIconOf(missao.icon), color: meta.color, size: 22),
          ),
          const SizedBox(width: BrandTokens.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  missao.titulo,
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  missao.descricao,
                  style: const TextStyle(
                    color: BrandTokens.textSecondary,
                    fontSize: 12,
                    height: 1.3,
                  ),
                ),
                const SizedBox(height: 6),
                Row(
                  children: [
                    Icon(meta.icon, size: 13, color: meta.color),
                    const SizedBox(width: 4),
                    Text(
                      meta.label,
                      style: TextStyle(
                        color: meta.color,
                        fontWeight: FontWeight.w800,
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: BrandTokens.spaceSm),
          Text(
            '+${missao.pontos}',
            style: const TextStyle(
              fontWeight: FontWeight.w900,
              fontSize: 16,
              color: BrandTokens.success,
            ),
          ),
        ],
      ),
    );
  }
}

class _BreakdownRow extends StatelessWidget {
  const _BreakdownRow({
    required this.icon,
    required this.label,
    required this.pontos,
  });
  final IconData icon;
  final String label;
  final String pontos;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, size: 18, color: BrandTokens.primary),
          const SizedBox(width: BrandTokens.spaceSm),
          Expanded(
            child: Text(
              label,
              style: const TextStyle(
                fontSize: 13.5,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Text(
            pontos,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w800,
              color: BrandTokens.success,
            ),
          ),
        ],
      ),
    );
  }
}

class _RecompensaCard extends ConsumerWidget {
  const _RecompensaCard({required this.recompensa});
  final RecompensaDto recompensa;

  Future<void> _resgatar(BuildContext context, WidgetRef ref) async {
    await Haptics.light();
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Resgatar recompensa?'),
        content: Text(
          '${recompensa.label}\n\nVamos descontar ${recompensa.pontos} pontos e enviar pra aprovação da nossa equipe.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Confirmar'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await ref
          .read(fidelidadeRepositoryProvider)
          .resgatar(recompensa.slug);
      ref.invalidate(fidelidadeProvider);
      if (!context.mounted) return;
      await Haptics.success();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Resgate solicitado! Vamos te avisar quando aprovar.'),
        ),
      );
    } on Object {
      if (!context.mounted) return;
      await Haptics.error();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Não consegui solicitar. Tente de novo.'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final habilitado = recompensa.disponivel;
    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceSm),
      child: Material(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        child: InkWell(
          borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
          onTap: habilitado ? () => _resgatar(context, ref) : null,
          child: Container(
            padding: const EdgeInsets.all(BrandTokens.spaceMd),
            decoration: BoxDecoration(
              border: Border.all(
                color: habilitado
                    ? BrandTokens.primary.withOpacity(0.30)
                    : BrandTokens.divider,
              ),
              borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
            ),
            child: Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: habilitado
                        ? BrandTokens.primary.withOpacity(0.14)
                        : Colors.black.withOpacity(0.04),
                    borderRadius:
                        BorderRadius.circular(BrandTokens.radiusMd),
                  ),
                  child: Icon(
                    Icons.card_giftcard_rounded,
                    color: habilitado
                        ? BrandTokens.primary
                        : BrandTokens.textSecondary,
                  ),
                ),
                const SizedBox(width: BrandTokens.spaceMd),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        recompensa.label,
                        style: TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 14.5,
                          color: habilitado
                              ? null
                              : BrandTokens.textSecondary,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '${recompensa.pontos} pontos',
                        style: TextStyle(
                          color: habilitado
                              ? BrandTokens.primary
                              : BrandTokens.textSecondary,
                          fontWeight: FontWeight.w700,
                          fontSize: 12.5,
                        ),
                      ),
                    ],
                  ),
                ),
                Icon(
                  habilitado
                      ? Icons.chevron_right_rounded
                      : Icons.lock_outline_rounded,
                  color: habilitado
                      ? BrandTokens.primary
                      : BrandTokens.textSecondary,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ResgateRow extends StatelessWidget {
  const _ResgateRow({required this.r});
  final ResgateDto r;

  (Color, String) _statusVisual() {
    switch (r.status) {
      case 'pendente':
        return (BrandTokens.warning, 'Aguardando aprovação');
      case 'aprovado':
        return (BrandTokens.info, 'Aprovado');
      case 'aplicado':
        return (BrandTokens.success, 'Aplicado');
      case 'rejeitado':
        return (BrandTokens.danger, 'Rejeitado');
      default:
        return (BrandTokens.textSecondary, r.status);
    }
  }

  @override
  Widget build(BuildContext context) {
    final (cor, statusLabel) = _statusVisual();
    final fmt = DateFormat('dd/MM HH:mm', 'pt_BR');
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Container(
        padding: const EdgeInsets.all(BrandTokens.spaceMd),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          border: Border.all(color: BrandTokens.divider),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    r.recompensaLabel,
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 13.5,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${r.pontosGastos} pts · ${fmt.format(r.criadoEm.toLocal())}',
                    style: const TextStyle(
                      color: BrandTokens.textSecondary,
                      fontSize: 11.5,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: BrandTokens.spaceSm,
                vertical: 3,
              ),
              decoration: BoxDecoration(
                color: cor.withOpacity(0.14),
                borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
              ),
              child: Text(
                statusLabel,
                style: TextStyle(
                  color: cor,
                  fontWeight: FontWeight.w800,
                  fontSize: 11,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RegrasInfo extends StatelessWidget {
  const _RegrasInfo();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceMd),
      decoration: BoxDecoration(
        color: BrandTokens.primary.withOpacity(0.06),
        borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.info_outline_rounded,
                  size: 16, color: BrandTokens.primary),
              SizedBox(width: 6),
              Text(
                'Como funciona',
                style: TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 13,
                  color: BrandTokens.primary,
                ),
              ),
            ],
          ),
          SizedBox(height: 6),
          Text(
            '• 10 pontos por mês de Ondeline\n'
            '• 50 pontos por fatura paga\n'
            '• Resgates passam por aprovação manual da nossa equipe (até 24h)',
            style: TextStyle(
              fontSize: 12.5,
              color: BrandTokens.textSecondary,
              height: 1.45,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
