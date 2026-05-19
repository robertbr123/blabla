import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';

final _osDetailProvider =
    FutureProvider.family<Map<String, dynamic>, String>((ref, id) async {
  final dio = ref.watch(apiClientProvider);
  final r = await dio.get('/api/v1/tecnico/me/os/$id');
  return (r.data as Map<String, dynamic>);
});

class OsDetailScreen extends ConsumerWidget {
  final String id;
  const OsDetailScreen({super.key, required this.id});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(_osDetailProvider(id));
    return Scaffold(
      appBar: AppBar(title: Text('OS')),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Erro: $e')),
        data: (os) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _Linha('Código', os['codigo']?.toString() ?? '—'),
            _Linha('Status', os['status']?.toString() ?? '—'),
            _Linha('Cliente', os['nome_cliente']?.toString() ?? '—'),
            _Linha('Problema', os['problema']?.toString() ?? '—', wrap: true),
            _Linha('Endereço', os['endereco']?.toString() ?? '—', wrap: true),
            if (os['plano'] != null) _Linha('Plano', os['plano'].toString()),
            const SizedBox(height: 24),
            // TODO M-mobile-3: botões "Iniciar visita" (GPS), "Concluir" (com
            // câmera antes/depois). Por enquanto, scaffold só de leitura —
            // veja core/sync/sync_service.dart para o plano da fila offline.
            const _PlaceholderAcoes(),
          ],
        ),
      ),
    );
  }
}

class _Linha extends StatelessWidget {
  final String label;
  final String value;
  final bool wrap;
  const _Linha(this.label, this.value, {this.wrap = false});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label.toUpperCase(),
            style: Theme.of(context)
                .textTheme
                .labelSmall
                ?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant),
          ),
          const SizedBox(height: 2),
          Text(value, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}

class _PlaceholderAcoes extends StatelessWidget {
  const _PlaceholderAcoes();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              const Icon(Icons.construction),
              const SizedBox(width: 8),
              Text('Ações virão no próximo PR',
                  style: Theme.of(context).textTheme.titleMedium),
            ]),
            const SizedBox(height: 8),
            const Text(
              '• Iniciar visita (com GPS)\n'
              '• Câmera antes/depois\n'
              '• Concluir com CSAT e relatório\n'
              '• Tudo funciona offline com fila local',
            ),
          ],
        ),
      ),
    );
  }
}
