import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/dto.dart';
import '../../core/api/indicacao_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/share/render_to_png.dart';
import '../../core/ui/haptics.dart';
import 'widgets/indicacao_share_card.dart';

class IndicacaoScreen extends ConsumerWidget {
  const IndicacaoScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(indicacaoMeuProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Indique e ganhe'),
        elevation: 0,
      ),
      body: async.when(
        data: (data) => RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(indicacaoMeuProvider);
            ref.invalidate(indicacaoTimelineProvider);
            await ref.read(indicacaoMeuProvider.future);
          },
          child: _Content(data: data),
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _ErrorView(
          message: e.toString(),
          onRetry: () => ref.invalidate(indicacaoMeuProvider),
        ),
      ),
    );
  }
}

class _Content extends ConsumerWidget {
  const _Content({required this.data});
  final IndicacaoMeuDto data;

  Future<void> _shareWhatsApp(BuildContext context, WidgetRef ref) async {
    if (data.linkCompartilhamento.isEmpty) {
      _toast(context, 'Número da empresa não configurado.');
      return;
    }
    final uri = Uri.tryParse(data.linkCompartilhamento);
    if (uri == null) {
      _toast(context, 'Link inválido.');
      return;
    }
    ref.read(indicacaoRepositoryProvider).registrarShare().then((_) {
      ref.invalidate(indicacaoMeuProvider);
    });
    await Haptics.success();
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _shareImage(BuildContext context, WidgetRef ref) async {
    final messenger = ScaffoldMessenger.of(context);
    messenger.showSnackBar(
      const SnackBar(
        duration: Duration(seconds: 2),
        content: Text('Gerando imagem…'),
      ),
    );
    try {
      final bytes = await renderWidgetToPng(
        IndicacaoShareCard(
          codigo: data.codigo,
          recompensa: data.milestone.recompensa,
        ),
        logicalSize: IndicacaoShareCard.designSize,
      );
      final tmp = await getTemporaryDirectory();
      final file = File('${tmp.path}/indicacao_${data.codigo}.png');
      await file.writeAsBytes(bytes, flush: true);
      ref.read(indicacaoRepositoryProvider).registrarShare().then((_) {
        ref.invalidate(indicacaoMeuProvider);
      });
      await Haptics.success();
      await Share.shareXFiles(
        [XFile(file.path, mimeType: 'image/png')],
        text:
            'Use meu código *${data.codigo}* pra contratar a internet — você ganha desconto e eu também 🚀',
      );
    } on Object catch (e) {
      messenger.showSnackBar(
        SnackBar(content: Text('Não consegui gerar a imagem: $e')),
      );
    }
  }

  Future<void> _copy(BuildContext context, String text, String label) async {
    await Clipboard.setData(ClipboardData(text: text));
    await Haptics.success();
    if (!context.mounted) return;
    _toast(context, '$label copiado.');
  }

  void _toast(BuildContext context, String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  void _showComoFunciona(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => Padding(
        padding: const EdgeInsets.all(BrandTokens.spaceLg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(bottom: BrandTokens.spaceMd),
              decoration: BoxDecoration(
                color: BrandTokens.divider,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            Text(
              'Como funciona',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: BrandTokens.spaceMd),
            _Step(
              n: 1,
              t: 'Compartilhe seu código',
              d: 'Envie pelo WhatsApp, posta no status ou nos grupos. Quanto mais gente vê, maior a chance.',
            ),
            _Step(
              n: 2,
              t: 'O amigo fecha plano',
              d: 'Quando ele virar cliente usando seu código, conta como uma indicação convertida.',
            ),
            _Step(
              n: 3,
              t: 'Você ganha a recompensa',
              d: 'Atingindo ${data.milestone.alvo} indicações convertidas, você ganha ${data.milestone.recompensa}. Fale com o suporte pra aplicar.',
            ),
            const SizedBox(height: BrandTokens.spaceMd),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Entendi'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return ListView(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      children: [
        _HeroCard(
          data: data,
          onCopyCodigo: () => _copy(context, data.codigo, 'Código'),
          onCopyLink: data.linkCompartilhamento.isEmpty
              ? null
              : () => _copy(context, data.linkCompartilhamento, 'Link'),
        ),
        const SizedBox(height: BrandTokens.spaceLg),

        // Progress bar de milestone
        _MilestoneCard(milestone: data.milestone, isDark: isDark),
        const SizedBox(height: BrandTokens.spaceLg),

        // CTAs de compartilhamento
        SizedBox(
          height: 56,
          child: FilledButton.icon(
            onPressed: () => _shareImage(context, ref),
            icon: const Icon(Icons.image_rounded),
            label: const Text('Compartilhar como imagem'),
            style: FilledButton.styleFrom(
              backgroundColor: BrandTokens.primary,
              foregroundColor: Colors.white,
              textStyle: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ),
        const SizedBox(height: BrandTokens.spaceSm),
        SizedBox(
          height: 52,
          child: OutlinedButton.icon(
            onPressed: () => _shareWhatsApp(context, ref),
            icon: const Icon(Icons.chat_rounded, color: Color(0xFF25D366)),
            label: const Text(
              'Enviar pelo WhatsApp',
              style: TextStyle(fontWeight: FontWeight.w800),
            ),
            style: OutlinedButton.styleFrom(
              side: const BorderSide(color: Color(0xFF25D366), width: 1.5),
              foregroundColor: const Color(0xFF128C7E),
            ),
          ),
        ),
        const SizedBox(height: BrandTokens.spaceXs),
        Center(
          child: TextButton(
            onPressed: () => _showComoFunciona(context),
            child: const Text(
              'Como funciona?',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
        ),
        const SizedBox(height: BrandTokens.spaceLg),

        // Stats
        _StatsCard(data: data, isDark: isDark),
        const SizedBox(height: BrandTokens.spaceLg),

        // Timeline
        const _TimelineSection(),
      ],
    );
  }
}

class _HeroCard extends StatelessWidget {
  const _HeroCard({
    required this.data,
    required this.onCopyCodigo,
    required this.onCopyLink,
  });
  final IndicacaoMeuDto data;
  final VoidCallback onCopyCodigo;
  final VoidCallback? onCopyLink;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        gradient: BrandTokens.gradientHero,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        boxShadow: BrandTokens.elevation2,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Row(
            children: [
              Icon(Icons.card_giftcard_rounded, color: Colors.white, size: 22),
              SizedBox(width: BrandTokens.spaceSm),
              Text(
                'Seu código',
                style: TextStyle(
                  color: Colors.white70,
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                ),
              ),
            ],
          ),
          const SizedBox(height: BrandTokens.spaceMd),
          Text(
            data.codigo,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w900,
              fontSize: 42,
              letterSpacing: 6,
            ),
          ),
          const SizedBox(height: BrandTokens.spaceMd),
          Row(
            children: [
              Expanded(
                child: _SmallActionButton(
                  icon: Icons.copy_rounded,
                  label: 'Copiar código',
                  onTap: onCopyCodigo,
                ),
              ),
              if (onCopyLink != null) ...[
                const SizedBox(width: BrandTokens.spaceSm),
                Expanded(
                  child: _SmallActionButton(
                    icon: Icons.link_rounded,
                    label: 'Copiar link',
                    onTap: onCopyLink!,
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}

class _MilestoneCard extends StatelessWidget {
  const _MilestoneCard({required this.milestone, required this.isDark});
  final IndicacaoMilestoneDto milestone;
  final bool isDark;

  @override
  Widget build(BuildContext context) {
    final atingido = milestone.atingido;
    final headline = atingido
        ? '🎉 Você desbloqueou ${milestone.recompensa}!'
        : '${milestone.faltam} ${milestone.faltam == 1 ? 'indicação' : 'indicações'} pra ganhar ${milestone.recompensa}';
    final sub = atingido
        ? 'Fale com o suporte pra aplicar o benefício na sua próxima fatura.'
        : '${milestone.atingidos} de ${milestone.alvo} amigos já fecharam plano com seu código.';

    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceMd),
      decoration: BoxDecoration(
        color: atingido
            ? BrandTokens.success.withOpacity(0.10)
            : (isDark ? BrandTokens.surfaceDark : BrandTokens.surface),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(
          color: atingido
              ? BrandTokens.success.withOpacity(0.40)
              : (isDark ? Colors.white12 : BrandTokens.divider),
        ),
        boxShadow: BrandTokens.elevation1,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            headline,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            sub,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: BrandTokens.textSecondary,
                ),
          ),
          const SizedBox(height: BrandTokens.spaceMd),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: milestone.progresso.toDouble(),
              minHeight: 12,
              backgroundColor: isDark
                  ? Colors.white12
                  : BrandTokens.primary.withOpacity(0.10),
              valueColor: AlwaysStoppedAnimation(
                atingido ? BrandTokens.success : BrandTokens.primary,
              ),
            ),
          ),
          const SizedBox(height: 6),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '${milestone.atingidos}',
                style: TextStyle(
                  color: BrandTokens.textSecondary,
                  fontWeight: FontWeight.w800,
                  fontSize: 12,
                ),
              ),
              Text(
                '${milestone.alvo}',
                style: const TextStyle(
                  color: BrandTokens.textSecondary,
                  fontWeight: FontWeight.w800,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatsCard extends StatelessWidget {
  const _StatsCard({required this.data, required this.isDark});
  final IndicacaoMeuDto data;
  final bool isDark;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceMd),
      decoration: BoxDecoration(
        color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(
          color: isDark ? Colors.white12 : BrandTokens.divider,
        ),
        boxShadow: BrandTokens.elevation1,
      ),
      child: Column(
        children: [
          Text(
            'Suas indicações',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: BrandTokens.spaceMd),
          Row(
            children: [
              Expanded(
                child: _Stat(
                  label: 'Cliques',
                  value: '${data.usos}',
                  color: BrandTokens.info,
                ),
              ),
              Expanded(
                child: _Stat(
                  label: 'Convertidos',
                  value: '${data.convertidos}',
                  color: BrandTokens.warning,
                ),
              ),
              Expanded(
                child: _Stat(
                  label: 'Creditados',
                  value: '${data.creditoAplicado}',
                  color: BrandTokens.success,
                ),
              ),
            ],
          ),
          if (data.usos == 0) ...[
            const SizedBox(height: BrandTokens.spaceMd),
            Text(
              'Compartilhe seu código pra começar a aparecer aqui.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: BrandTokens.textSecondary,
                  ),
            ),
          ],
        ],
      ),
    );
  }
}

class _TimelineSection extends ConsumerWidget {
  const _TimelineSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(indicacaoTimelineProvider);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Atividade recente',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w800,
              ),
        ),
        const SizedBox(height: BrandTokens.spaceSm),
        async.when(
          data: (items) {
            if (items.isEmpty) {
              return Container(
                padding: const EdgeInsets.all(BrandTokens.spaceLg),
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: BrandTokens.surface,
                  borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
                  border: Border.all(color: BrandTokens.divider),
                ),
                child: Text(
                  'Nada aqui ainda. Quando alguém usar seu código, a atividade aparece neste lugar.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: BrandTokens.textSecondary,
                      ),
                ),
              );
            }
            return Column(
              children: [
                for (final it in items) _TimelineTile(item: it),
              ],
            );
          },
          loading: () => const Padding(
            padding: EdgeInsets.all(BrandTokens.spaceLg),
            child: Center(child: CircularProgressIndicator()),
          ),
          error: (_, __) => Text(
            'Não consegui carregar a atividade.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: BrandTokens.danger,
                ),
          ),
        ),
      ],
    );
  }
}

class _TimelineTile extends StatelessWidget {
  const _TimelineTile({required this.item});
  final IndicacaoTimelineItemDto item;

  ({Color color, IconData icon, String label, DateTime when}) get _meta {
    switch (item.status) {
      case 'creditado':
        return (
          color: BrandTokens.success,
          icon: Icons.verified_rounded,
          label: 'Crédito aplicado',
          when: item.creditoAplicadoEm ?? item.criadoEm,
        );
      case 'convertido':
        return (
          color: BrandTokens.warning,
          icon: Icons.handshake_rounded,
          label: 'Virou cliente',
          when: item.convertidoEm ?? item.criadoEm,
        );
      default:
        return (
          color: BrandTokens.info,
          icon: Icons.touch_app_rounded,
          label: 'Recebido no funil',
          when: item.criadoEm,
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final meta = _meta;
    final df = DateFormat('dd/MM');
    return Container(
      margin: const EdgeInsets.only(bottom: BrandTokens.spaceSm),
      padding: const EdgeInsets.all(BrandTokens.spaceMd),
      decoration: BoxDecoration(
        color: BrandTokens.surface,
        borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
        border: Border.all(color: BrandTokens.divider),
      ),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: meta.color.withOpacity(0.14),
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Icon(meta.icon, color: meta.color, size: 18),
          ),
          const SizedBox(width: BrandTokens.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.nomeMascarado,
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 14,
                  ),
                ),
                Text(
                  meta.label,
                  style: const TextStyle(
                    color: BrandTokens.textSecondary,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          Text(
            df.format(meta.when),
            style: const TextStyle(
              color: BrandTokens.textSecondary,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _SmallActionButton extends StatelessWidget {
  const _SmallActionButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white.withOpacity(0.18),
      borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: BrandTokens.spaceSm,
            vertical: BrandTokens.spaceSm,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: Colors.white, size: 16),
              const SizedBox(width: 6),
              Flexible(
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  softWrap: false,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
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

class _Stat extends StatelessWidget {
  const _Stat({
    required this.label,
    required this.value,
    required this.color,
  });
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(
            color: color,
            fontWeight: FontWeight.w900,
            fontSize: 26,
          ),
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: BrandTokens.textSecondary,
                fontWeight: FontWeight.w600,
              ),
        ),
      ],
    );
  }
}

class _Step extends StatelessWidget {
  const _Step({required this.n, required this.t, required this.d});
  final int n;
  final String t;
  final String d;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceMd),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: BrandTokens.primary.withOpacity(0.14),
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Text(
              '$n',
              style: const TextStyle(
                color: BrandTokens.primary,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          const SizedBox(width: BrandTokens.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  t,
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 2),
                Text(
                  d,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: BrandTokens.textSecondary,
                      ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final friendlier = message.contains('409')
        ? 'Sua conta ainda não esta vinculada ao cadastro de cliente. Entre em contato com o suporte.'
        : 'Não conseguimos carregar agora. Tente novamente em instantes.';
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(BrandTokens.spaceLg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.error_outline,
              color: BrandTokens.danger,
              size: 40,
            ),
            const SizedBox(height: BrandTokens.spaceMd),
            Text(friendlier, textAlign: TextAlign.center),
            const SizedBox(height: BrandTokens.spaceLg),
            FilledButton(onPressed: onRetry, child: const Text('Tentar de novo')),
          ],
        ),
      ),
    );
  }
}
