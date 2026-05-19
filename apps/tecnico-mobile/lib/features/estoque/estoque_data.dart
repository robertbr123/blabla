import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';

class EstoqueLinha {
  final String itemId;
  final String sku;
  final String nome;
  final String categoria;
  final bool serializado;
  final int saldo;

  EstoqueLinha({
    required this.itemId,
    required this.sku,
    required this.nome,
    required this.categoria,
    required this.serializado,
    required this.saldo,
  });

  factory EstoqueLinha.fromJson(Map<String, dynamic> j) => EstoqueLinha(
        itemId: (j['item_id'] ?? '') as String,
        sku: (j['sku'] ?? '') as String,
        nome: (j['nome'] ?? '') as String,
        categoria: (j['categoria'] ?? '') as String,
        serializado: (j['serializado'] ?? false) as bool,
        saldo: (j['saldo'] ?? 0) as int,
      );
}

/// Saldo do estoque do tecnico logado.
final estoqueSaldoProvider =
    FutureProvider<List<EstoqueLinha>>((ref) async {
  final dio = ref.watch(apiClientProvider);
  final r = await dio.get('/api/v1/tecnico/me/estoque/saldo');
  final raw = r.data as Map<String, dynamic>;
  final linhas = (raw['linhas'] as List).cast<Map<String, dynamic>>();
  return linhas.map(EstoqueLinha.fromJson).toList();
});
