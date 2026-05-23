import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/contatos_repository.dart';
import '../../core/api/dto.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/haptics.dart';

class ContatosScreen extends ConsumerWidget {
  const ContatosScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(contatosOperadoraProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Fale conosco')),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(contatosOperadoraProvider);
          await ref.read(contatosOperadoraProvider.future);
        },
        child: async.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => _Empty(
            icon: Icons.error_outline_rounded,
            label: 'Não foi possível carregar.',
            sub: 'Puxa pra baixo pra tentar de novo.',
          ),
          data: (list) {
            if (list.isEmpty) {
              return _Empty(
                icon: Icons.contact_support_outlined,
                label: 'Sem contatos configurados ainda.',
                sub: 'Em breve nossa equipe vai disponibilizar aqui.',
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.all(BrandTokens.spaceLg),
              itemCount: list.length,
              separatorBuilder: (_, __) =>
                  const SizedBox(height: BrandTokens.spaceSm),
              itemBuilder: (_, i) => _ContatoCard(contato: list[i]),
            );
          },
        ),
      ),
    );
  }
}

class _ContatoCard extends StatelessWidget {
  const _ContatoCard({required this.contato});
  final ContatoOperadoraDto contato;

  (IconData, Color) _visual() {
    switch (contato.tipo) {
      case 'whatsapp':
        return (Icons.chat_bubble_rounded, const Color(0xFF25D366));
      case 'telefone':
        return (Icons.phone_rounded, BrandTokens.primary);
      case 'email':
        return (Icons.email_outlined, BrandTokens.info);
      case 'endereco':
        return (Icons.location_on_outlined, BrandTokens.warning);
      case 'instagram':
        return (Icons.camera_alt_outlined, const Color(0xFFE1306C));
      case 'facebook':
        return (Icons.facebook, const Color(0xFF1877F2));
      case 'site':
        return (Icons.language_rounded, BrandTokens.primaryDark);
      default:
        return (Icons.help_outline_rounded, BrandTokens.textSecondary);
    }
  }

  Future<void> _acionar(BuildContext context) async {
    await Haptics.light();
    final uri = _toUri(contato);
    if (uri == null) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(contato.valor)),
        );
      }
      return;
    }
    try {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } on Object {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Não consegui abrir esse contato.')),
      );
    }
  }

  static Uri? _toUri(ContatoOperadoraDto c) {
    switch (c.tipo) {
      case 'whatsapp':
        final num = c.valor.replaceAll(RegExp(r'\D'), '');
        if (num.isEmpty) return null;
        return Uri.parse('https://wa.me/$num');
      case 'telefone':
        final num = c.valor.replaceAll(RegExp(r'[^0-9+]'), '');
        return Uri.parse('tel:$num');
      case 'email':
        return Uri.parse('mailto:${c.valor.trim()}');
      case 'endereco':
        return Uri.parse(
          'https://www.google.com/maps/search/?api=1&query=${Uri.encodeComponent(c.valor)}',
        );
      case 'instagram':
      case 'facebook':
      case 'site':
        final v = c.valor.trim();
        if (v.startsWith('http')) return Uri.parse(v);
        return Uri.parse('https://$v');
      default:
        return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final (icon, color) = _visual();
    return Material(
      color: Theme.of(context).colorScheme.surface,
      borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
      child: InkWell(
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        onTap: () => _acionar(context),
        child: Container(
          padding: const EdgeInsets.all(BrandTokens.spaceMd),
          decoration: BoxDecoration(
            border: Border.all(
              color: Theme.of(context).brightness == Brightness.dark
                  ? Colors.white12
                  : BrandTokens.divider,
            ),
            borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
          ),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: color.withOpacity(0.14),
                  borderRadius:
                      BorderRadius.circular(BrandTokens.radiusMd),
                ),
                alignment: Alignment.center,
                child: Icon(icon, color: color, size: 22),
              ),
              const SizedBox(width: BrandTokens.spaceMd),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      contato.label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 15,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      contato.valor,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: BrandTokens.textSecondary,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    if (contato.subtitle != null &&
                        contato.subtitle!.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        contato.subtitle!,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: BrandTokens.textSecondary,
                          fontSize: 11.5,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
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
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty({required this.icon, required this.label, required this.sub});
  final IconData icon;
  final String label;
  final String sub;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        const SizedBox(height: 120),
        Icon(icon, size: 64, color: BrandTokens.textSecondary),
        const SizedBox(height: BrandTokens.spaceMd),
        Text(
          label,
          textAlign: TextAlign.center,
          style: Theme.of(context)
              .textTheme
              .titleMedium
              ?.copyWith(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: BrandTokens.spaceXs),
        Padding(
          padding:
              const EdgeInsets.symmetric(horizontal: BrandTokens.spaceLg),
          child: Text(
            sub,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: BrandTokens.textSecondary,
              fontSize: 13,
            ),
          ),
        ),
      ],
    );
  }
}
