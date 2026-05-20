import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/session_cleanup.dart';
import '../../core/theme.dart';
import '../../core/ui/app_section_header.dart';
import '../../core/ui/app_surfaces.dart';
import '../../core/push/fcm_service.dart';
import '../../core/sync/sync_service.dart';
import 'os_data.dart';
import 'widgets/home_filter_strip.dart';
import 'widgets/home_hero.dart';
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
  OsHomeFilter _selectedFilter = OsHomeFilter.pendente;

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(osListStreamProvider);
    final pendingSync = ref.watch(pendingCountProvider);
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: scheme.surfaceContainerLowest,
      appBar: AppBar(
        title: const Text('Home'),
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
        loading: () => const Center(child: CircularProgressIndicator()),
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
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.only(top: 8, bottom: 24),
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 0),
                  child: HomeHero(
                    total: items.length,
                    pendentes: counts['pendente'] ?? 0,
                    andamento: counts['em_andamento'] ?? 0,
                    nextAt: _nextScheduledAt(items),
                  ),
                ),
                if (pendingSync case AsyncData(:final value)
                    when value > 0) ...[
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                    child: _OfflineQueueBanner(count: value),
                  ),
                ],
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                  child: AppSectionHeader(
                    title: 'Pulso operacional',
                    subtitle:
                        'Atalhos rápidos para a fila que precisa da sua atenção.',
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  height: 160,
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
                        color: brandAccent,
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
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 20, 16, 0),
                  child: HomeFilterStrip(
                    filters: _filters,
                    selected: _selectedFilter,
                    onSelected: _selectFilter,
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 20, 16, 0),
                  child: AppSectionHeader(
                    title: _selectedFilter.listTitle,
                    subtitle: _selectedFilter.listSubtitle(filtered.length),
                    actionLabel:
                        _selectedFilter == OsHomeFilter.todas ? null : 'Todas',
                    onAction: _selectedFilter == OsHomeFilter.todas
                        ? null
                        : () => _selectFilter(OsHomeFilter.todas),
                  ),
                ),
                if (filtered.isEmpty)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                    child: _EstadoVazio(
                      filter: _selectedFilter,
                      onRefresh: () => ref.invalidate(osListStreamProvider),
                    ),
                  )
                else
                  ...filtered.map(
                    (it) => OsCard(
                      id: it.id,
                      codigo: it.codigo,
                      status: it.status,
                      problema: it.problema,
                      endereco: it.endereco,
                      nomeCliente: it.nomeCliente,
                      agendamentoAt: it.agendamentoAt,
                      onTap: () => context.push('/os/${it.id}'),
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

  DateTime? _nextScheduledAt(List<_OsItem> items) {
    for (final item in items) {
      if (item.agendamentoAt != null) {
        return item.agendamentoAt;
      }
    }
    return null;
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
              color: brandAccent.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              Icons.cloud_upload_rounded,
              size: 18,
              color: brandAccent,
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
    String texto;
    IconData icone;
    switch (filter) {
      case OsHomeFilter.todas:
        texto = 'Nenhuma OS atribuída a você.';
        icone = Icons.inbox_outlined;
        break;
      case OsHomeFilter.pendente:
        texto = 'Nenhuma OS pendente.';
        icone = Icons.check_circle_outline;
        break;
      case OsHomeFilter.andamento:
        texto = 'Nenhuma OS em andamento.';
        icone = Icons.directions_run;
        break;
      case OsHomeFilter.concluida:
        texto = 'Nenhuma OS concluída ainda.';
        icone = Icons.check_circle_outline;
        break;
      case OsHomeFilter.cancelada:
        texto = 'Nenhuma OS cancelada.';
        icone = Icons.cancel_outlined;
        break;
    }
    return AppSurfaceCard(
      padding: const EdgeInsets.fromLTRB(20, 32, 20, 32),
      child: Column(
        children: [
          Icon(
            icone,
            size: 56,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: 16),
          Text(
            texto,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: onRefresh,
            icon: const Icon(Icons.refresh),
            label: const Text('Atualizar'),
          ),
        ],
      ),
    );
  }
}

class _Erro extends StatelessWidget {
  final Object e;
  final VoidCallback onRetry;
  const _Erro({required this.e, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        const Icon(Icons.error_outline, size: 56),
        const SizedBox(height: 12),
        Text(e.toString(), textAlign: TextAlign.center),
        const SizedBox(height: 12),
        FilledButton(onPressed: onRetry, child: const Text('Tentar de novo')),
      ]),
    );
  }
}
