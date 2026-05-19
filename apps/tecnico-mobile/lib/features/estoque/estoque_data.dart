import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/auth/auth_storage.dart';
import '../../core/db/database.dart';
import '../../core/db/estoque_repo.dart';

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

final estoqueLocalRepoProvider = Provider<EstoqueLocalRepo>((ref) {
  return EstoqueLocalRepo(ref.watch(dbProvider));
});

final estoqueAuthUserIdProvider = FutureProvider<String?>((ref) {
  return readUserId();
});

/// Saldo do estoque do tecnico logado.
final estoqueSaldoProvider = FutureProvider<List<EstoqueLinha>>((ref) async {
  final repo = ref.watch(estoqueLocalRepoProvider);
  final userId = await ref.watch(estoqueAuthUserIdProvider.future);
  final cached = await _loadCachedRows(repo: repo, userId: userId);

  try {
    final dio = ref.watch(apiClientProvider);
    final r = await dio.get('/api/v1/tecnico/me/estoque/saldo');
    final raw = r.data as Map<String, dynamic>;
    final linhas = _decodeRows(raw);
    if (userId != null && userId.isNotEmpty) {
      await repo.replaceAll(userId: userId, rows: linhas);
    }
    return linhas.map(EstoqueLinha.fromJson).toList();
  } on DioException {
    if (cached.isNotEmpty) {
      return cached.map(EstoqueLinha.fromJson).toList();
    }
    rethrow;
  }
});

Future<List<Map<String, dynamic>>> _loadCachedRows({
  required EstoqueLocalRepo repo,
  required String? userId,
}) {
  if (userId == null || userId.isEmpty) {
    return Future.value(const <Map<String, dynamic>>[]);
  }
  return repo.listAll(userId: userId);
}

List<Map<String, dynamic>> _decodeRows(Map<String, dynamic> raw) {
  final linhas = (raw['linhas'] as List? ?? const [])
      .whereType<Map>()
      .map((row) => row.cast<String, dynamic>())
      .toList();
  return linhas;
}
