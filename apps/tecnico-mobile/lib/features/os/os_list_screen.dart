import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/api/api_client.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/push/fcm_service.dart';

class OsListItem {
  final String id;
  final String codigo;
  final String status;
  final String problema;
  final String endereco;
  final String? nomeCliente;
  final DateTime? agendamentoAt;

  OsListItem({
    required this.id,
    required this.codigo,
    required this.status,
    required this.problema,
    required this.endereco,
    required this.nomeCliente,
    required this.agendamentoAt,
  });

  factory OsListItem.fromJson(Map<String, dynamic> j) => OsListItem(
        id: j['id'] as String,
        codigo: j['codigo'] as String,
        status: j['status'] as String,
        problema: (j['problema'] ?? '') as String,
        endereco: (j['endereco'] ?? '') as String,
        nomeCliente: j['nome_cliente'] as String?,
        agendamentoAt: j['agendamento_at'] != null
            ? DateTime.tryParse(j['agendamento_at'] as String)
            : null,
      );
}

final _osListProvider = FutureProvider<List<OsListItem>>((ref) async {
  final dio = ref.watch(apiClientProvider);
  final r = await dio.get('/api/v1/tecnico/me/os');
  final raw = r.data;
  final List items;
  if (raw is List) {
    items = raw;
  } else if (raw is Map && raw['items'] is List) {
    items = raw['items'] as List;
  } else {
    items = const [];
  }
  return items
      .cast<Map<String, dynamic>>()
      .map(OsListItem.fromJson)
      .toList();
});

class OsListScreen extends ConsumerWidget {
  const OsListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(_osListProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Minhas OS'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(_osListProvider),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sair',
            onPressed: () async {
              // Revoga token FCM antes de derrubar a sessao.
              try {
                await ref.read(fcmServiceProvider).revoke();
              } catch (_) {}
              await ref.read(authRepositoryProvider).logout();
              ref.invalidate(hasTokenProvider);
              if (context.mounted) context.go('/login');
            },
          ),
        ],
      ),
      body: async.when(
        data: (items) => items.isEmpty
            ? const Center(child: Text('Nenhuma OS atribuída.'))
            : RefreshIndicator(
                onRefresh: () async => ref.invalidate(_osListProvider),
                child: ListView.separated(
                  itemCount: items.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (_, i) => _OsTile(item: items[i]),
                ),
              ),
        error: (e, _) => _ErrorView(
          error: e,
          onRetry: () => ref.invalidate(_osListProvider),
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
      ),
    );
  }
}

class _OsTile extends StatelessWidget {
  final OsListItem item;
  const _OsTile({required this.item});

  Color _statusColor(BuildContext ctx) {
    switch (item.status) {
      case 'pendente':
        return Colors.orange;
      case 'em_andamento':
        return Theme.of(ctx).colorScheme.primary;
      case 'concluida':
        return Colors.green;
      case 'cancelada':
        return Colors.grey;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final agend = item.agendamentoAt;
    return ListTile(
      onTap: () => context.push('/os/${item.id}'),
      title: Text(
        '${item.codigo} · ${item.nomeCliente ?? "—"}',
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(item.problema, maxLines: 2, overflow: TextOverflow.ellipsis),
          const SizedBox(height: 4),
          Text(
            item.endereco,
            style: Theme.of(context).textTheme.bodySmall,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          if (agend != null)
            Text(
              '📅 ${DateFormat('dd/MM HH:mm').format(agend.toLocal())}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
        ],
      ),
      trailing: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: _statusColor(context).withOpacity(0.15),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(
          item.status,
          style: TextStyle(
            color: _statusColor(context),
            fontWeight: FontWeight.w600,
            fontSize: 11,
          ),
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final Object error;
  final VoidCallback onRetry;
  const _ErrorView({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    final msg = error is DioException
        ? (error as DioException).message ?? error.toString()
        : error.toString();
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 56),
          const SizedBox(height: 12),
          Text(msg, textAlign: TextAlign.center),
          const SizedBox(height: 16),
          FilledButton(onPressed: onRetry, child: const Text('Tentar de novo')),
        ],
      ),
    );
  }
}
