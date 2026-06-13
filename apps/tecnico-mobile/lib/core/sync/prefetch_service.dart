import 'dart:async';
import 'dart:developer' as developer;

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../auth/auth_storage.dart';
import '../db/cliente_cadastro_repo.dart';
import '../db/database.dart';
import '../db/estoque_repo.dart';

/// Aquece o cache offline (estoque + lista de clientes) proativamente, pra o
/// fallback cache-first ter dados mesmo se o técnico não abriu as telas online.
class PrefetchService {
  final Dio _dio;
  final AppDatabase _db;
  StreamSubscription<List<ConnectivityResult>>? _connSub;
  bool _running = false;

  PrefetchService(this._dio, this._db);

  /// Prefetch inicial + re-prefetch quando a rede volta. Idempotente.
  Future<void> start() async {
    unawaited(prefetchAll());
    _connSub ??= Connectivity().onConnectivityChanged.listen((results) {
      final online = results.any((r) => r != ConnectivityResult.none);
      if (online) unawaited(prefetchAll());
    });
  }

  Future<void> stop() async {
    await _connSub?.cancel();
    _connSub = null;
  }

  /// Best-effort: aquece o cache. Não lança (warm-up). Não-reentrante.
  Future<void> prefetchAll() async {
    if (_running) return;
    _running = true;
    try {
      final userId = await readUserId();
      if (userId == null || userId.isEmpty) return;
      await _prefetchEstoque(userId);
      await _prefetchClientes(userId);
    } finally {
      _running = false;
    }
  }

  Future<void> _prefetchEstoque(String userId) async {
    try {
      final r = await _dio.get('/api/v1/tecnico/me/estoque/saldo');
      final raw = r.data as Map<String, dynamic>;
      final rows = (raw['linhas'] as List? ?? const [])
          .whereType<Map>()
          .map((m) => m.cast<String, dynamic>())
          .toList();
      await EstoqueLocalRepo(_db).replaceAll(userId: userId, rows: rows);
    } catch (e) {
      developer.log('prefetch estoque falhou',
          name: 'PrefetchService', error: e);
    }
  }

  Future<void> _prefetchClientes(String userId) async {
    try {
      final r = await _dio.get('/api/v1/clientes-campo');
      final raw = r.data as Map<String, dynamic>;
      final rows = (raw['items'] as List? ?? const [])
          .whereType<Map>()
          .map((m) => m.cast<String, dynamic>())
          .toList();
      await ClienteCadastroLocalRepo(_db).replaceAll(userId: userId, rows: rows);
    } catch (e) {
      developer.log('prefetch clientes falhou',
          name: 'PrefetchService', error: e);
    }
  }
}

final prefetchServiceProvider = Provider<PrefetchService>((ref) {
  final svc =
      PrefetchService(ref.watch(apiClientProvider), ref.watch(dbProvider));
  ref.onDispose(svc.stop);
  return svc;
});
