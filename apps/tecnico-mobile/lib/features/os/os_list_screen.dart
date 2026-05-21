import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/session_cleanup.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/app_section_header.dart';
import '../../core/ui/app_state_panel.dart';
import '../../core/ui/app_surfaces.dart';
import '../../core/push/fcm_service.dart';
import '../../core/sync/sync_service.dart';
import 'os_data.dart';
import 'widgets/home_filter_strip.dart';
import 'widgets/home_summary_card.dart';
import 'widgets/os_card.dart';

class _OsItem {
  final String id;
  final String codigo;
  final String status;
  final String problema;
  final String endereco;
  final String? nomeCliente;
  final DateTime? agendamentoAt;
  final DateTime? criadaEm;

  _OsItem({
    required this.id,
    required this.codigo,
    required this.status,
    required this.problema,
    required this.endereco,
    required this.nomeCliente,
    required this.agendamentoAt,
    required this.criadaEm,
  });

  factory _OsItem.fromJson(Map<String, dynamic> j) => _OsItem(
        id: j['id'] as String,
        codigo: (j['codigo'] ?? '') as String,
        status: (j['status'] ?? '') as String,
        problema: (j['problema'] ?? '') as String,
        endereco: (j['endereco'] ?? '') as String,
        nomeCliente: j['nome_cliente'] as String?,
        agendamentoAt: j['agendamento_at'] != null
            ? DateTime.tryParse(j['agendamento_at'] as String)
            : null,
        criadaEm: j['criada_em'] != null
            ? DateTime.tryParse(j['criada_em'] as String)
            : null,
      );
}

class OsListScreen extends ConsumerStatefulWidget {
  const OsListScreen({super.key});

  @override
  ConsumerState<OsListScreen> createState() => _OsListScreenState();
}

class _OsListScreenState extends ConsumerState<OsListScreen> {
  static const _filters = OsHomeFilter.values;
  OsHomeFilter _selectedFilter = OsHomeFilter.todas;

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(osListStreamProvider);
    final pendingSync = ref.watch(pendingCountProvider);
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: scheme.surface,
      appBar: AppBar(
        toolbarHeight: 48,
        backgroundColor: scheme.surface,
        elevation: 0,
        scrolledUnderElevation: 0,
        automaticallyImplyLeading: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Atualizar',
            onPressed: () => ref.invalidate(osListStreamProvider),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sair',
            onPressed: _logout,
          ),
        ],
      ),
      body: async.when(
        loading: () => const _StateBody(
          child: AppStatePanel.loading(
            title: 'Atualizando sua fila',
            message:
                'Buscando o panorama mais recente das OS para abrir seu turno com contexto.',
          ),
        ),
        error: (e, _) => _Erro(
          e: e,
          onRetry: () => ref.invalidate(osListStreamProvider),
        ),
        data: (rows) {
          final items = rows.map(_OsItem.fromJson).toList()
            ..sort((a, b) => _sortKey(a).compareTo(_sortKey(b)));
          final counts = _countByStatus(items);
          final filtered = items
              .where((item) => _selectedFilter.matches(item.status))
              .toList();

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(osListStreamProvider),
            child: CustomScrollView(
              key: const ValueKey('os-home-scroll'),
              physics: const AlwaysScrollableScrollPhysics(),
              slivers: [
                if (pendingSync case AsyncData(:final value) when value > 0)
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                      child: _OfflineQueueBanner(count: value),
                    ),
                  ),
                const SliverToBoxAdapter(
                  child: Padding(
                    padding: EdgeInsets.fromLTRB(16, 12, 16, 0),
                    child: AppSectionHeader(
                      title: 'Pulso operacional',
                      subtitle:
                          'Atalhos rápidos para a fila que precisa da sua atenção.',
                    ),
                  ),
                ),
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: SizedBox(
                      height: 124,
                      child: ListView(
                        scrollDirection: Axis.horizontal,
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        children: [
                          HomeSummaryCard(
                            key: const ValueKey('home-summary-pendentes'),
                            label: 'Pendentes',
                            value: counts['pendente'] ?? 0,
                            subtitle: 'Aguardando visita',
                            icon: Icons.hourglass_top_rounded,
                            color: BrandTokens.warningLight,
                            selected: _selectedFilter == OsHomeFilter.pendente,
                            onTap: () => _selectFilter(OsHomeFilter.pendente),
                          ),
                          const SizedBox(width: 12),
                          HomeSummaryCard(
                            key: const ValueKey('home-summary-andamento'),
                            label: 'Em andamento',
                            value: counts['em_andamento'] ?? 0,
                            subtitle: 'Visitas em curso',
                            icon: Icons.route_rounded,
                            color: scheme.primary,
                            selected: _selectedFilter == OsHomeFilter.andamento,
                            onTap: () => _selectFilter(OsHomeFilter.andamento),
                          ),
                          const SizedBox(width: 12),
                          HomeSummaryCard(
                            key: const ValueKey('home-summary-concluidas'),
                            label: 'Concluídas',
                            value: counts['concluida'] ?? 0,
                            subtitle: 'Encerradas hoje',
                            icon: Icons.check_circle_rounded,
                            color: scheme.tertiary,
                            selected: _selectedFilter == OsHomeFilter.concluida,
                            onTap: () => _selectFilter(OsHomeFilter.concluida),
                          ),
                          const SizedBox(width: 12),
                          HomeSummaryCard(
                            key: const ValueKey('home-summary-canceladas'),
                            label: 'Canceladas',
                            value: counts['cancelada'] ?? 0,
                            subtitle: 'Exigem revisão',
                            icon: Icons.cancel_rounded,
                            color: scheme.error,
                            selected: _selectedFilter == OsHomeFilter.cancelada,
                            onTap: () => _selectFilter(OsHomeFilter.cancelada),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                    child: HomeFilterStrip(
                      filters: _filters,
                      selected: _selectedFilter,
                      onSelected: _selectFilter,
                    ),
                  ),
                ),
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
                    child: AppSectionHeader(
                      title: _selectedFilter.listTitle,
                      subtitle: _selectedFilter.listSubtitle(filtered.length),
                      actionLabel: _selectedFilter == OsHomeFilter.todas
                          ? null
                          : 'Todas',
                      onAction: _selectedFilter == OsHomeFilter.todas
                          ? null
                          : () => _selectFilter(OsHomeFilter.todas),
                    ),
                  ),
                ),
                if (filtered.isEmpty)
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
                      child: _EstadoVazio(
                        filter: _selectedFilter,
                        onRefresh: () => ref.invalidate(osListStreamProvider),
                      ),
                    ),
                  )
                else
                  SliverPadding(
                    padding: const EdgeInsets.only(bottom: 24),
                    sliver: SliverList(
                      delegate: SliverChildBuilderDelegate(
                        (context, index) {
                          final it = filtered[index];
                          return OsCard(
                            id: it.id,
                            codigo: it.codigo,
                            status: it.status,
                            problema: it.problema,
                            endereco: it.endereco,
                            nomeCliente: it.nomeCliente,
                            agendamentoAt: it.agendamentoAt,
                            onTap: () => context.push('/os/${it.id}'),
                          );
                        },
                        childCount: filtered.length,
                      ),
                    ),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }

  void _selectFilter(OsHomeFilter filter) {
    if (_selectedFilter == filter) return;
    setState(() => _selectedFilter = filter);
  }

  // Ordena: atrasadas/agendamento mais próximo primeiro; sem agendamento
  // por criada_em mais recente.
  int _sortKey(_OsItem i) {
    final now = DateTime.now().millisecondsSinceEpoch;
    if (i.agendamentoAt != null) {
      return i.agendamentoAt!.millisecondsSinceEpoch;
    }
    if (i.criadaEm != null) {
      // OS sem agendamento, mas com data de criação, vai depois das agendadas,
      // mais recente primeiro
      return now + (now - i.criadaEm!.millisecondsSinceEpoch);
    }
    return now * 2;
  }

  Map<String, int> _countByStatus(List<_OsItem> items) {
    final m = <String, int>{};
    for (final it in items) {
      m[it.status] = (m[it.status] ?? 0) + 1;
    }
    return m;
  }

  Future<void> _logout() async {
    try {
      await ref.read(fcmServiceProvider).revoke();
    } catch (_) {}
    await ref.read(authRepositoryProvider).logout();
    await ref.read(sessionCleanupProvider).clearLocalSession();
    if (mounted) context.go('/login');
  }
}

class _OfflineQueueBanner extends StatelessWidget {
  final int count;
  const _OfflineQueueBanner({required this.count});

  @override
  Widget build(BuildContext context) {
    return AppSurfaceCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Row(
        children: [
          Container(
            height: 36,
            width: 36,
            decoration: BoxDecoration(
              color: BrandTokens.infoLight.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(
              Icons.cloud_upload_rounded,
              size: 18,
              color: BrandTokens.infoLight,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Fila offline pronta para sincronizar',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  '$count ${count == 1 ? "item" : "itens"} aguardando upload',
                  style: TextStyle(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
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

class _EstadoVazio extends StatelessWidget {
  final OsHomeFilter filter;
  final VoidCallback onRefresh;
  const _EstadoVazio({required this.filter, required this.onRefresh});

  @override
  Widget build(BuildContext context) {
    String title;
    String texto;
    IconData icone;
    switch (filter) {
      case OsHomeFilter.todas:
        title = 'Nenhuma OS disponível';
        texto = 'Nenhuma OS atribuída a você.';
        icone = Icons.inbox_outlined;
        break;
      case OsHomeFilter.pendente:
        title = 'Tudo em dia por aqui';
        texto = 'Nenhuma OS pendente precisa da sua atenção agora.';
        icone = Icons.check_circle_outline;
        break;
      case OsHomeFilter.andamento:
        title = 'Sem visitas em andamento';
        texto = 'Sua fila ativa está livre no momento.';
        icone = Icons.directions_run;
        break;
      case OsHomeFilter.concluida:
        title = 'Sem OS concluídas ainda';
        texto = 'As conclusões do dia vão aparecer aqui assim que fecharem.';
        icone = Icons.check_circle_outline;
        break;
      case OsHomeFilter.cancelada:
        title = 'Nenhuma OS cancelada';
        texto = 'Quando houver cancelamentos para revisar, eles aparecem aqui.';
        icone = Icons.cancel_outlined;
        break;
    }
    return AppStatePanel.empty(
      title: title,
      message: texto,
      icon: icone,
      actionLabel: 'Atualizar',
      onAction: onRefresh,
    );
  }
}

class _Erro extends StatelessWidget {
  final Object e;
  final VoidCallback onRetry;
  const _Erro({required this.e, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    final panel = isOfflineException(e)
        ? AppStatePanel.offline(
            title: 'Sem conexão para atualizar a fila',
            message:
                'A última sincronização não chegou agora. Revise sua conexão e tente novamente em instantes.',
            actionLabel: 'Tentar novamente',
            onAction: onRetry,
          )
        : AppStatePanel.error(
            title: 'Não foi possível carregar sua fila',
            message:
                'Algo impediu a atualização das OS. Tente novamente para retomar o painel operacional.',
            actionLabel: 'Tentar novamente',
            onAction: onRetry,
          );

    return _StateBody(child: panel);
  }
}

class _StateBody extends StatelessWidget {
  final Widget child;
  const _StateBody({required this.child});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 440),
          child: child,
        ),
      ),
    );
  }
}
