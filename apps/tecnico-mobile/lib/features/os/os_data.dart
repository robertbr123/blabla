import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/db/database.dart';
import '../../core/db/os_repo.dart';

final _osRepoProvider = Provider<OsLocalRepo>((ref) {
  return OsLocalRepo(ref.watch(dbProvider));
});

/// Lista de OS — usa cache local (Stream Drift) e refresca em background.
/// Offline = última snapshot fica visível.
final osListStreamProvider =
    StreamProvider<List<Map<String, dynamic>>>((ref) async* {
  final repo = ref.watch(_osRepoProvider);
  final cached = await repo.listAll();

  if (cached.isNotEmpty) {
    yield cached;
    Future<void>.microtask(() async {
      try {
        await _refreshOsList(ref, repo);
      } on DioException {
        // offline: stream do cache continua respondendo
      } catch (_) {
        // ignora demais erros — UI mostra cache
      }
    });
    yield* repo.watchAll().skip(1);
    return;
  }

  await _refreshOsList(ref, repo);
  yield* repo.watchAll();
});

/// Detalhe de OS — read-through similar.
final osDetailProvider =
    FutureProvider.family<Map<String, dynamic>, String>((ref, id) async {
  final repo = ref.watch(_osRepoProvider);
  // 1. tenta API se conseguir
  try {
    final dio = ref.read(apiClientProvider);
    final r = await dio.get('/api/v1/tecnico/me/os/$id');
    final m = r.data as Map<String, dynamic>;
    await repo.upsertOne(m);
    return m;
  } on DioException {
    // 2. fallback no cache
    final cached = await repo.getById(id);
    if (cached != null) return cached;
    rethrow;
  }
});

/// Provider expondo o repo pra logout limpar cache.
final osLocalRepoProvider =
    Provider<OsLocalRepo>((ref) => ref.watch(_osRepoProvider));

Future<void> _refreshOsList(Ref ref, OsLocalRepo repo) async {
  final dio = ref.read(apiClientProvider);
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
  await repo.reconcileWithServer(items.cast<Map<String, dynamic>>());
}
