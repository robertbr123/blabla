import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/session_cleanup.dart';
import '../../core/push/fcm_service.dart';
import '../../core/sync/sync_service.dart';
import 'os_data.dart';
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

enum _Aba { todas, pendente, andamento, concluida, cancelada }

extension _AbaLabel on _Aba {
  String get label {
    switch (this) {
      case _Aba.todas:
        return 'Todas';
      case _Aba.pendente:
        return 'Pendentes';
      case _Aba.andamento:
        return 'Andamento';
      case _Aba.concluida:
        return 'Concluídas';
      case _Aba.cancelada:
        return 'Canceladas';
    }
  }

  bool matches(String s) {
    switch (this) {
      case _Aba.todas:
        return true;
      case _Aba.pendente:
        return s == 'pendente';
      case _Aba.andamento:
        return s == 'em_andamento';
      case _Aba.concluida:
        return s == 'concluida';
      case _Aba.cancelada:
        return s == 'cancelada';
    }
  }
}

class OsListScreen extends ConsumerStatefulWidget {
  const OsListScreen({super.key});

  @override
  ConsumerState<OsListScreen> createState() => _OsListScreenState();
}

class _OsListScreenState extends ConsumerState<OsListScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tab;
  static const _abas = _Aba.values;

  @override
  void initState() {
    super.initState();
    _tab = TabController(length: _abas.length, vsync: this);
    // Default abre em "Pendentes" — onde técnico mais opera.
    _tab.index = _Aba.pendente.index;
    _tab.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _tab.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(osListStreamProvider);
    final pendingSync = ref.watch(pendingCountProvider);
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: scheme.surfaceContainerLowest,
      appBar: AppBar(
        title: const Text('Minhas OS'),
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
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(48),
          child: TabBar(
            controller: _tab,
            isScrollable: true,
            tabAlignment: TabAlignment.start,
            tabs: _abas.map((a) => Tab(text: a.label)).toList(),
          ),
        ),
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
          return Column(
            children: [
              pendingSync.when(
                data: (n) => n > 0
                    ? _OfflineQueueBanner(count: n)
                    : const SizedBox.shrink(),
                loading: () => const SizedBox.shrink(),
                error: (_, __) => const SizedBox.shrink(),
              ),
              _SummaryStrip(
                counts: _countByStatus(items),
                onTap: (aba) => _tab.animateTo(aba.index),
                selected: _abas[_tab.index],
              ),
              const SizedBox(height: 4),
              Expanded(
                child: TabBarView(
                  controller: _tab,
                  children: _abas.map((aba) {
                    final filtered =
                        items.where((i) => aba.matches(i.status)).toList();
                    if (filtered.isEmpty) {
                      return _EstadoVazio(
                        aba: aba,
                        onRefresh: () => ref.invalidate(osListStreamProvider),
                      );
                    }
                    return RefreshIndicator(
                      onRefresh: () async =>
                          ref.invalidate(osListStreamProvider),
                      child: ListView.builder(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.only(top: 4, bottom: 16),
                        itemCount: filtered.length,
                        itemBuilder: (_, i) {
                          final it = filtered[i];
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
                      ),
                    );
                  }).toList(),
                ),
              ),
            ],
          );
        },
      ),
    );
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

class _SummaryStrip extends StatelessWidget {
  final Map<String, int> counts;
  final void Function(_Aba) onTap;
  final _Aba selected;
  const _SummaryStrip({
    required this.counts,
    required this.onTap,
    required this.selected,
  });

  @override
  Widget build(BuildContext context) {
    final pend = counts['pendente'] ?? 0;
    final and = counts['em_andamento'] ?? 0;
    final conc = counts['concluida'] ?? 0;
    final canc = counts['cancelada'] ?? 0;

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      child: Row(
        children: [
          _Kpi(
            label: 'Pendentes',
            value: pend,
            color: const Color(0xFFf59e0b),
            icon: Icons.hourglass_top,
            selected: selected == _Aba.pendente,
            onTap: () => onTap(_Aba.pendente),
          ),
          const SizedBox(width: 8),
          _Kpi(
            label: 'Em andamento',
            value: and,
            color: const Color(0xFF2563eb),
            icon: Icons.directions_run,
            selected: selected == _Aba.andamento,
            onTap: () => onTap(_Aba.andamento),
          ),
          const SizedBox(width: 8),
          _Kpi(
            label: 'Concluídas',
            value: conc,
            color: const Color(0xFF16a34a),
            icon: Icons.check_circle,
            selected: selected == _Aba.concluida,
            onTap: () => onTap(_Aba.concluida),
          ),
          const SizedBox(width: 8),
          _Kpi(
            label: 'Canceladas',
            value: canc,
            color: const Color(0xFF6b7280),
            icon: Icons.cancel,
            selected: selected == _Aba.cancelada,
            onTap: () => onTap(_Aba.cancelada),
          ),
        ],
      ),
    );
  }
}

class _Kpi extends StatelessWidget {
  final String label;
  final int value;
  final Color color;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;
  const _Kpi({
    required this.label,
    required this.value,
    required this.color,
    required this.icon,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        width: 120,
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        decoration: BoxDecoration(
          color: selected
              ? color.withValues(alpha: 0.15)
              : scheme.surfaceContainerHigh,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: selected ? color : scheme.outlineVariant,
            width: selected ? 1.5 : 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 14, color: color),
                const Spacer(),
                Text(
                  '$value',
                  style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    color: scheme.onSurface,
                    height: 1,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                color: scheme.onSurfaceVariant,
                fontWeight: FontWeight.w600,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}

class _OfflineQueueBanner extends StatelessWidget {
  final int count;
  const _OfflineQueueBanner({required this.count});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 8, 12, 0),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFf59e0b).withValues(alpha: 0.13),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: const Color(0xFFf59e0b).withValues(alpha: 0.35),
        ),
      ),
      child: Row(
        children: [
          const Icon(Icons.cloud_upload, size: 16, color: Color(0xFFd97706)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              '$count ${count == 1 ? "item" : "itens"} aguardando upload',
              style: const TextStyle(
                color: Color(0xFFb45309),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _EstadoVazio extends StatelessWidget {
  final _Aba aba;
  final VoidCallback onRefresh;
  const _EstadoVazio({required this.aba, required this.onRefresh});

  @override
  Widget build(BuildContext context) {
    String texto;
    IconData icone;
    switch (aba) {
      case _Aba.todas:
        texto = 'Nenhuma OS atribuída a você.';
        icone = Icons.inbox_outlined;
        break;
      case _Aba.pendente:
        texto = 'Nenhuma OS pendente. 🎉';
        icone = Icons.check_circle_outline;
        break;
      case _Aba.andamento:
        texto = 'Nenhuma OS em andamento.';
        icone = Icons.directions_run;
        break;
      case _Aba.concluida:
        texto = 'Nenhuma OS concluída ainda.';
        icone = Icons.check_circle_outline;
        break;
      case _Aba.cancelada:
        texto = 'Nenhuma OS cancelada.';
        icone = Icons.cancel_outlined;
        break;
    }
    return RefreshIndicator(
      onRefresh: () async => onRefresh(),
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          const SizedBox(height: 80),
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
