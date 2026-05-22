import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/dto.dart';
import '../../core/api/faturas_repository.dart';
import '../../core/branding/brand_tokens.dart';
import 'widgets/fatura_bottom_sheet.dart';

class FaturasScreen extends ConsumerStatefulWidget {
  const FaturasScreen({super.key});

  @override
  ConsumerState<FaturasScreen> createState() => _FaturasScreenState();
}

class _FaturasScreenState extends ConsumerState<FaturasScreen> {
  int? _anoFiltro; // null = todas

  @override
  Widget build(BuildContext context) {
    final abertasAsync = ref.watch(faturasAbertasProvider);
    final pagasAsync = ref.watch(faturasPagasProvider);

    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: RefreshIndicator(
          onRefresh: () async {
            // Força refresh no backend (invalida cache SGP de 1h) — usuario
            // chamando pull-to-refresh espera dado novo, ex: depois que admin
            // baixou fatura no SGP.
            await ref.read(faturasRepositoryProvider).refreshAll();
            ref.invalidate(faturasAbertasProvider);
            ref.invalidate(faturasPagasProvider);
          },
          child: ListView(
            physics: const BouncingScrollPhysics(
              parent: AlwaysScrollableScrollPhysics(),
            ),
            padding: const EdgeInsets.fromLTRB(
              BrandTokens.spaceLg,
              BrandTokens.spaceLg,
              BrandTokens.spaceLg,
              120,
            ),
            children: [
              Text(
                'Faturas',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceLg),
              abertasAsync.when(
                loading: () => const _HeroSkeleton(),
                error: (_, __) => _ErrorCard(
                  onRetry: () =>
                      ref.invalidate(faturasAbertasProvider),
                ),
                data: (abertas) {
                  if (abertas.isEmpty) {
                    return const _EmAdiaCard();
                  }
                  // Pega a mais proxima do vencimento (primeira da lista,
                  // ja vem ordenada do backend).
                  final principal = abertas.first;
                  final outras = abertas.skip(1).toList();
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _AbertaHeroCard(
                        fatura: principal,
                        onTap: () =>
                            FaturaBottomSheet.show(context, principal),
                      ),
                      if (outras.isNotEmpty) ...[
                        const SizedBox(height: BrandTokens.spaceMd),
                        ...outras.map(
                          (f) => _OutraAbertaTile(
                            fatura: f,
                            onTap: () =>
                                FaturaBottomSheet.show(context, f),
                          ),
                        ),
                      ],
                    ],
                  );
                },
              ),
              const SizedBox(height: BrandTokens.spaceXl),
              _SectionLabel(label: 'Historico'),
              const SizedBox(height: BrandTokens.spaceSm),
              pagasAsync.when(
                loading: () => const Padding(
                  padding: EdgeInsets.symmetric(vertical: BrandTokens.spaceLg),
                  child: Center(child: CircularProgressIndicator()),
                ),
                error: (_, __) => const SizedBox.shrink(),
                data: (pagas) {
                  if (pagas.isEmpty) {
                    return _MutedText(
                      'Suas faturas pagas vao aparecer aqui.',
                    );
                  }
                  // Anos disponiveis pra filtrar
                  final anos = pagas
                      .map((f) => f.vencimentoDate.year)
                      .toSet()
                      .toList()
                    ..sort((a, b) => b.compareTo(a));
                  final filtradas = _anoFiltro == null
                      ? pagas
                      : pagas
                          .where((f) => f.vencimentoDate.year == _anoFiltro)
                          .toList();
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      if (anos.length > 1)
                        _AnoFilter(
                          anos: anos,
                          selecionado: _anoFiltro,
                          onSelect: (a) =>
                              setState(() => _anoFiltro = a),
                        ),
                      const SizedBox(height: BrandTokens.spaceMd),
                      for (int i = 0; i < filtradas.length; i++)
                        _TimelineTile(
                          fatura: filtradas[i],
                          isFirst: i == 0,
                          isLast: i == filtradas.length - 1,
                          onTap: () =>
                              FaturaBottomSheet.show(context, filtradas[i]),
                        ),
                    ],
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ════════ Hero da fatura em aberto ════════

class _AbertaHeroCard extends StatelessWidget {
  const _AbertaHeroCard({required this.fatura, required this.onTap});
  final FaturaDto fatura;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final fmtValor = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
    final fmtData = DateFormat('dd/MM/yyyy', 'pt_BR');
    final venceHoje = _diasAteVencimento(fatura.vencimentoDate);
    final statusColor =
        fatura.isVencido ? BrandTokens.danger : Colors.white;
    final statusTexto = _heroStatusTexto(fatura, venceHoje);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
      child: Container(
        padding: const EdgeInsets.all(BrandTokens.spaceLg),
        decoration: BoxDecoration(
          gradient: fatura.isVencido
              ? const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    BrandTokens.danger,
                    Color(0xFFB12B40),
                  ],
                )
              : BrandTokens.gradientHero,
          borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
          boxShadow: BrandTokens.elevation2,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 5,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.18),
                    borderRadius:
                        BorderRadius.circular(BrandTokens.radiusSm),
                    border: Border.all(
                      color: Colors.white.withOpacity(0.30),
                    ),
                  ),
                  child: Text(
                    statusTexto,
                    style: TextStyle(
                      color: statusColor,
                      fontWeight: FontWeight.w800,
                      fontSize: 11,
                      letterSpacing: 0.3,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: BrandTokens.spaceMd),
            Text(
              fmtValor.format(fatura.valor),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 36,
                fontWeight: FontWeight.w900,
                letterSpacing: -1,
              ),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                const Icon(
                  Icons.calendar_today_outlined,
                  color: Colors.white70,
                  size: 14,
                ),
                const SizedBox(width: 6),
                Text(
                  'Vence ${fmtData.format(fatura.vencimentoDate)}',
                  style: const TextStyle(
                    color: Colors.white70,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: BrandTokens.spaceLg),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: BrandTokens.spaceMd,
                vertical: BrandTokens.spaceSm,
              ),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.18),
                borderRadius:
                    BorderRadius.circular(BrandTokens.radiusMd),
              ),
              child: Row(
                children: [
                  if (fatura.temPix) ...[
                    const Icon(Icons.qr_code_2_rounded,
                        color: Colors.white, size: 20),
                    const SizedBox(width: BrandTokens.spaceSm),
                    const Text(
                      'Pagar com Pix',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ] else if (fatura.temPdf) ...[
                    const Icon(Icons.picture_as_pdf_outlined,
                        color: Colors.white, size: 20),
                    const SizedBox(width: BrandTokens.spaceSm),
                    const Text(
                      'Abrir boleto',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                  const Spacer(),
                  const Icon(
                    Icons.arrow_forward_rounded,
                    color: Colors.white,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  int _diasAteVencimento(DateTime venc) {
    final hoje = DateTime.now();
    final v = DateTime(venc.year, venc.month, venc.day);
    final h = DateTime(hoje.year, hoje.month, hoje.day);
    return v.difference(h).inDays;
  }

  String _heroStatusTexto(FaturaDto f, int dias) {
    if (f.isVencido) return 'VENCIDA HA ${f.diasAtraso} DIA${f.diasAtraso == 1 ? '' : 'S'}';
    if (dias == 0) return 'VENCE HOJE';
    if (dias == 1) return 'VENCE AMANHA';
    if (dias > 0) return 'VENCE EM $dias DIAS';
    return 'EM ABERTO';
  }
}

// ════════ Outras abertas (compactas) ════════

class _OutraAbertaTile extends StatelessWidget {
  const _OutraAbertaTile({required this.fatura, required this.onTap});
  final FaturaDto fatura;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final fmtValor = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
    final fmtData = DateFormat('dd/MM', 'pt_BR');
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceSm),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          child: Container(
            padding: const EdgeInsets.all(BrandTokens.spaceMd),
            decoration: BoxDecoration(
              color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
              borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
              border: Border.all(
                color: fatura.isVencido
                    ? BrandTokens.danger.withOpacity(0.30)
                    : (isDark ? Colors.white12 : BrandTokens.divider),
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: (fatura.isVencido
                            ? BrandTokens.danger
                            : BrandTokens.warning)
                        .withOpacity(0.14),
                    borderRadius:
                        BorderRadius.circular(BrandTokens.radiusSm),
                  ),
                  child: Icon(
                    fatura.isVencido
                        ? Icons.warning_amber_rounded
                        : Icons.schedule_rounded,
                    size: 18,
                    color: fatura.isVencido
                        ? BrandTokens.danger
                        : BrandTokens.warning,
                  ),
                ),
                const SizedBox(width: BrandTokens.spaceMd),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        fmtValor.format(fatura.valor),
                        style: const TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 15,
                        ),
                      ),
                      Text(
                        fatura.isVencido
                            ? 'Vencida ${fmtData.format(fatura.vencimentoDate)}'
                            : 'Vence ${fmtData.format(fatura.vencimentoDate)}',
                        style: TextStyle(
                          color: fatura.isVencido
                              ? BrandTokens.danger
                              : BrandTokens.textSecondary,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
                const Icon(
                  Icons.chevron_right_rounded,
                  color: BrandTokens.textSecondary,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ════════ Timeline (pagas) ════════

class _TimelineTile extends StatelessWidget {
  const _TimelineTile({
    required this.fatura,
    required this.isFirst,
    required this.isLast,
    required this.onTap,
  });
  final FaturaDto fatura;
  final bool isFirst;
  final bool isLast;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final fmtValor = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
    final fmtMes = DateFormat('MMM/yyyy', 'pt_BR');
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Trilho vertical + bolinha
          SizedBox(
            width: 32,
            child: Column(
              children: [
                SizedBox(
                  height: 12,
                  child: isFirst
                      ? const SizedBox.shrink()
                      : Container(
                          width: 2,
                          color: BrandTokens.success.withOpacity(0.30),
                        ),
                ),
                Container(
                  width: 14,
                  height: 14,
                  decoration: BoxDecoration(
                    color: BrandTokens.success,
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: isDark
                          ? BrandTokens.backgroundDark
                          : BrandTokens.background,
                      width: 3,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: BrandTokens.success.withOpacity(0.30),
                        blurRadius: 8,
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: isLast
                      ? const SizedBox.shrink()
                      : Container(
                          width: 2,
                          color: BrandTokens.success.withOpacity(0.30),
                        ),
                ),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: BrandTokens.spaceMd),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: onTap,
                  borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
                  child: Padding(
                    padding: const EdgeInsets.all(BrandTokens.spaceMd),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                fmtValor.format(fatura.valor),
                                style: const TextStyle(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 15,
                                ),
                              ),
                              Text(
                                fmtMes.format(fatura.vencimentoDate),
                                style: const TextStyle(
                                  color: BrandTokens.textSecondary,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color:
                                BrandTokens.success.withOpacity(0.14),
                            borderRadius:
                                BorderRadius.circular(BrandTokens.radiusSm),
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                Icons.check_circle,
                                color: BrandTokens.success,
                                size: 14,
                              ),
                              SizedBox(width: 4),
                              Text(
                                'Paga',
                                style: TextStyle(
                                  color: BrandTokens.success,
                                  fontWeight: FontWeight.w800,
                                  fontSize: 11,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ════════ Helpers ════════

class _SectionLabel extends StatelessWidget {
  const _SectionLabel({required this.label});
  final String label;
  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: Theme.of(context).textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.w800,
            letterSpacing: -0.2,
          ),
    );
  }
}

class _MutedText extends StatelessWidget {
  const _MutedText(this.text);
  final String text;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: BrandTokens.spaceMd),
      child: Text(
        text,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: BrandTokens.textSecondary,
            ),
      ),
    );
  }
}

class _EmAdiaCard extends StatelessWidget {
  const _EmAdiaCard();
  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        color: BrandTokens.success.withOpacity(0.10),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(
          color: BrandTokens.success.withOpacity(0.30),
        ),
      ),
      child: Column(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: BrandTokens.success.withOpacity(0.18),
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.check_circle_outline,
              color: BrandTokens.success,
              size: 30,
            ),
          ),
          const SizedBox(height: BrandTokens.spaceMd),
          Text(
            'Voce esta em dia! 🎉',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: isDark
                      ? BrandTokens.textPrimaryDark
                      : BrandTokens.textPrimary,
                ),
          ),
          const SizedBox(height: BrandTokens.spaceXs),
          Text(
            'Nenhuma fatura em aberto no momento.',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: BrandTokens.textSecondary,
                ),
          ),
        ],
      ),
    );
  }
}

class _HeroSkeleton extends StatelessWidget {
  const _HeroSkeleton();
  @override
  Widget build(BuildContext context) {
    return Container(
      height: 200,
      decoration: BoxDecoration(
        color: BrandTokens.primary.withOpacity(0.08),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
      ),
      child: const Center(child: CircularProgressIndicator()),
    );
  }
}

class _ErrorCard extends StatelessWidget {
  const _ErrorCard({required this.onRetry});
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        color: BrandTokens.danger.withOpacity(0.08),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
      ),
      child: Column(
        children: [
          const Icon(Icons.error_outline, color: BrandTokens.danger),
          const SizedBox(height: BrandTokens.spaceSm),
          const Text('Nao conseguimos carregar suas faturas.'),
          TextButton(
            onPressed: onRetry,
            child: const Text('Tentar de novo'),
          ),
        ],
      ),
    );
  }
}

class _AnoFilter extends StatelessWidget {
  const _AnoFilter({
    required this.anos,
    required this.selecionado,
    required this.onSelect,
  });
  final List<int> anos;
  final int? selecionado;
  final ValueChanged<int?> onSelect;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          _Chip(
            label: 'Todas',
            selecionado: selecionado == null,
            onTap: () => onSelect(null),
          ),
          for (final a in anos)
            _Chip(
              label: '$a',
              selecionado: selecionado == a,
              onTap: () => onSelect(a),
            ),
        ],
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({
    required this.label,
    required this.selecionado,
    required this.onTap,
  });
  final String label;
  final bool selecionado;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.only(right: BrandTokens.spaceSm),
      child: Material(
        color: selecionado
            ? BrandTokens.primary
            : (isDark ? BrandTokens.surfaceDark : BrandTokens.surface),
        borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: BrandTokens.spaceMd,
              vertical: BrandTokens.spaceSm,
            ),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
              border: Border.all(
                color: selecionado
                    ? BrandTokens.primary
                    : (isDark ? Colors.white12 : BrandTokens.divider),
              ),
            ),
            child: Text(
              label,
              style: TextStyle(
                color: selecionado ? Colors.white : null,
                fontWeight: selecionado ? FontWeight.w800 : FontWeight.w600,
                fontSize: 13,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
