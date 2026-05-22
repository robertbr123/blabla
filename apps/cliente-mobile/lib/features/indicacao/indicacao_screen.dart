import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/dto.dart';
import '../../core/api/indicacao_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/haptics.dart';

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
        data: (data) => _Content(data: data),
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
      _toast(context, 'Numero da empresa nao configurado.');
      return;
    }
    final uri = Uri.tryParse(data.linkCompartilhamento);
    if (uri == null) {
      _toast(context, 'Link invalido.');
      return;
    }
    // Registra evento server-side em paralelo (fire-and-forget). Invalida
    // o provider depois pra atualizar contador local.
    ref.read(indicacaoRepositoryProvider).registrarShare().then((_) {
      ref.invalidate(indicacaoMeuProvider);
    });
    await Haptics.success();
    await launchUrl(uri, mode: LaunchMode.externalApplication);
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
            const _Step(n: 1, t: 'Compartilhe seu link', d: 'Envie pelo WhatsApp pra amigos, familia ou nos grupos.'),
            const _Step(n: 2, t: 'O amigo fecha plano', d: 'Quando ele virar cliente Ondeline usando seu codigo, voce e ele ganham desconto.'),
            const _Step(n: 3, t: 'Receba o desconto', d: 'O desconto aparece automaticamente na proxima fatura dos dois.'),
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
        // Card hero com o codigo
        Container(
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
                    'Seu codigo',
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
                      label: 'Copiar codigo',
                      onTap: () => _copy(context, data.codigo, 'Codigo'),
                    ),
                  ),
                  const SizedBox(width: BrandTokens.spaceSm),
                  if (data.linkCompartilhamento.isNotEmpty)
                    Expanded(
                      child: _SmallActionButton(
                        icon: Icons.link_rounded,
                        label: 'Copiar link',
                        onTap: () => _copy(
                          context,
                          data.linkCompartilhamento,
                          'Link',
                        ),
                      ),
                    ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: BrandTokens.spaceLg),

        // CTA principal: compartilhar
        SizedBox(
          height: 56,
          child: FilledButton.icon(
            onPressed: () => _shareWhatsApp(context, ref),
            icon: const Icon(Icons.share_rounded),
            label: const Text('Compartilhar via WhatsApp'),
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFF25D366),
              foregroundColor: Colors.white,
              textStyle: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ),
        const SizedBox(height: BrandTokens.spaceXs),
        TextButton(
          onPressed: () => _showComoFunciona(context),
          child: const Text(
            'Como funciona?',
            style: TextStyle(fontWeight: FontWeight.w700),
          ),
        ),
        const SizedBox(height: BrandTokens.spaceLg),

        // Stats
        Container(
          padding: const EdgeInsets.all(BrandTokens.spaceMd),
          decoration: BoxDecoration(
            color: isDark
                ? BrandTokens.surfaceDark
                : BrandTokens.surface,
            borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
            border: Border.all(
              color: isDark ? Colors.white12 : BrandTokens.divider,
            ),
            boxShadow: BrandTokens.elevation1,
          ),
          child: Column(
            children: [
              Text(
                'Suas indicacoes',
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
                  'Compartilhe seu codigo pra comecar a aparecer aqui.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: BrandTokens.textSecondary,
                      ),
                ),
              ],
            ],
          ),
        ),
      ],
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
            horizontal: BrandTokens.spaceMd,
            vertical: BrandTokens.spaceSm,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: Colors.white, size: 16),
              const SizedBox(width: 6),
              Text(
                label,
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                  fontSize: 12,
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
        ? 'Sua conta ainda nao esta vinculada ao cadastro de cliente. Entre em contato com o suporte.'
        : 'Nao conseguimos carregar agora. Tente novamente em instantes.';
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
