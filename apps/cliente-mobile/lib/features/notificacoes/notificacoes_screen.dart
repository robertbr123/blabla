import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/dto.dart';
import '../../core/api/notificacoes_repository.dart';
import '../../core/api/os_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../nps/nps_bottom_sheet.dart';

const _categoriaCor = <String, Color>{
  'fatura': BrandTokens.catBilling,
  'os': BrandTokens.catSupport,
  'manutencao': BrandTokens.warning,
  'promocao': BrandTokens.catPlan,
  'conta': BrandTokens.info,
  'outro': BrandTokens.textSecondary,
};

const _categoriaIcon = <String, IconData>{
  'fatura': Icons.receipt_long_rounded,
  'os': Icons.support_agent_rounded,
  'manutencao': Icons.build_rounded,
  'promocao': Icons.local_offer_rounded,
  'conta': Icons.person_rounded,
  'outro': Icons.notifications_rounded,
};

class NotificacoesScreen extends ConsumerWidget {
  const NotificacoesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(notificacoesProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notificações'),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.done_all_rounded),
            tooltip: 'Marcar todas como lidas',
            onPressed: () async {
              await ref
                  .read(notificacoesRepositoryProvider)
                  .marcarTodasLidas();
              ref.invalidate(notificacoesProvider);
              ref.invalidate(notificacoesUnreadCountProvider);
            },
          ),
          IconButton(
            icon: const Icon(Icons.settings_rounded),
            tooltip: 'Preferências',
            onPressed: () => context.push('/notificacoes/preferencias'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(notificacoesProvider);
          ref.invalidate(notificacoesUnreadCountProvider);
          await ref.read(notificacoesProvider.future);
        },
        child: async.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => const Center(
            child: Text('Não conseguimos carregar as notificações.'),
          ),
          data: (lista) {
            if (lista.isEmpty) return const _Empty();
            return ListView.separated(
              physics: const BouncingScrollPhysics(
                parent: AlwaysScrollableScrollPhysics(),
              ),
              padding: const EdgeInsets.symmetric(
                vertical: BrandTokens.spaceMd,
              ),
              itemCount: lista.length,
              separatorBuilder: (_, __) => const Divider(
                height: 1,
                indent: 72,
                color: Color(0x11000000),
              ),
              itemBuilder: (_, i) => _NotifTile(notif: lista[i]),
            );
          },
        ),
      ),
    );
  }
}

class _NotifTile extends ConsumerWidget {
  const _NotifTile({required this.notif});
  final NotificacaoDto notif;

  Future<void> _onTap(BuildContext context, WidgetRef ref) async {
    // Marca como lida fire-and-forget.
    if (!notif.lida) {
      ref
          .read(notificacoesRepositoryProvider)
          .marcarLida(notif.id)
          .then((_) {
        ref.invalidate(notificacoesProvider);
        ref.invalidate(notificacoesUnreadCountProvider);
      });
    }
    final action = notif.action;
    if (action == null || action.isEmpty) return;
    if (action.startsWith('url:')) {
      final uri = Uri.tryParse(action.substring(4));
      if (uri != null) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
    } else if (action.startsWith('tela:')) {
      if (!context.mounted) return;
      // ignore: use_build_context_synchronously
      context.push(action.substring(5));
    } else if (action.startsWith('nps:')) {
      final osId = action.substring(4);
      // Tenta enriquecer com tipo/numero da OS, se a lista ja estiver no cache.
      final osAsync = ref.read(osListProvider);
      OsDto? os;
      osAsync.whenData((list) {
        for (final o in list) {
          if (o.id == osId) {
            os = o;
            break;
          }
        }
      });
      if (!context.mounted) return;
      // ignore: use_build_context_synchronously
      await showNpsBottomSheet(
        context,
        osId: osId,
        tipoLabel: os?.tipoLabel,
        numero: os != null ? _osNumeroCurto(osId) : null,
        teveVisitaTecnica: os?.teveVisitaTecnica ?? false,
      );
    }
  }

  static String _osNumeroCurto(String osId) {
    final clean = osId.replaceAll('-', '');
    return clean.length <= 6
        ? clean.toUpperCase()
        : clean.substring(0, 6).toUpperCase();
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cor = _categoriaCor[notif.categoria] ?? BrandTokens.primary;
    final ico = _categoriaIcon[notif.categoria] ?? Icons.notifications_rounded;
    final fmtData = DateFormat('dd/MM HH:mm', 'pt_BR');
    return Material(
      color: notif.lida
          ? Colors.transparent
          : BrandTokens.primary.withOpacity(0.04),
      child: InkWell(
        onTap: () => _onTap(context, ref),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: BrandTokens.spaceLg,
            vertical: BrandTokens.spaceMd,
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: cor.withOpacity(0.14),
                  borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
                ),
                child: Icon(ico, color: cor, size: 20),
              ),
              const SizedBox(width: BrandTokens.spaceMd),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            notif.titulo,
                            style: TextStyle(
                              fontWeight: notif.lida
                                  ? FontWeight.w600
                                  : FontWeight.w800,
                              fontSize: 14,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        if (!notif.lida)
                          Container(
                            width: 8,
                            height: 8,
                            margin: const EdgeInsets.only(left: 6, top: 4),
                            decoration: const BoxDecoration(
                              color: BrandTokens.primary,
                              shape: BoxShape.circle,
                            ),
                          ),
                      ],
                    ),
                    if (notif.corpo.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        notif.corpo,
                        style: const TextStyle(
                          fontSize: 13,
                          color: BrandTokens.textSecondary,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    const SizedBox(height: 4),
                    Text(
                      fmtData.format(notif.createdAt.toLocal()),
                      style: const TextStyle(
                        fontSize: 11,
                        color: BrandTokens.textSecondary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty();
  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      children: const [
        SizedBox(height: 120),
        Padding(
          padding: EdgeInsets.all(BrandTokens.spaceXl),
          child: Column(
            children: [
              Icon(
                Icons.notifications_off_outlined,
                size: 56,
                color: BrandTokens.textSecondary,
              ),
              SizedBox(height: BrandTokens.spaceMd),
              Text(
                'Sem notificações por aqui',
                style: TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 16,
                ),
              ),
              SizedBox(height: BrandTokens.spaceXs),
              Text(
                'Avisos importantes (fatura, OS, manutenção, promoção) aparecem aqui.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: BrandTokens.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
