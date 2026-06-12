import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../db/database.dart';
import 'outbox_repo.dart';

DateTime computeNextRetryAt({
  required int attempts,
  required DateTime createdAt,
  required DateTime? lastAttemptAt,
}) {
  final base = lastAttemptAt ?? createdAt;
  final waitSec = (1 << attempts.clamp(0, 8)).clamp(2, 300);
  return base.add(Duration(seconds: waitSec));
}

bool shouldAttemptAt(OutboxItemData item, DateTime now) {
  if (item.attempts == 0) return true;
  final nextRetryAt = computeNextRetryAt(
    attempts: item.attempts,
    createdAt: item.createdAt,
    lastAttemptAt: item.lastAttemptAt,
  );
  return !now.isBefore(nextRetryAt);
}

bool isRetryableSyncError(DioException error) {
  final code = error.response?.statusCode;
  if (code == null) {
    return error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.sendTimeout ||
        error.type == DioExceptionType.receiveTimeout;
  }

  return code == 408 || code == 429 || code >= 500;
}

/// Processa a fila offline (OutboxItem) em FIFO com backoff exponencial.
///
/// - Conectividade: usa connectivity_plus pra disparar flush quando rede volta
/// - Per-item backoff: 2^attempts segundos (clamp 5min)
/// - 4xx → marca como erro permanente (pula no proximo flush mas conta attempts)
/// - 5xx / network → retry no proximo flush
///
/// Idempotency: por enquanto confia que o backend nao processa duplicado se a
/// mesma OS+kind for enviada de novo. Quando o backend expor X-Idempotency-Key
/// (ver TODO em backend), adicionar header aqui.
class SyncService {
  final Dio _dio;
  final AppDatabase _db;
  late final OutboxRepo _outbox;
  StreamSubscription<List<ConnectivityResult>>? _connSub;
  Timer? _periodicTimer;
  bool _flushing = false;

  SyncService(this._dio, this._db) {
    _outbox = OutboxRepo(_db);
  }

  /// Inicia o listener de conectividade + flush periodico (a cada 60s).
  /// Idempotente.
  Future<void> start() async {
    _connSub ??= Connectivity().onConnectivityChanged.listen((results) {
      final online = results.any((r) => r != ConnectivityResult.none);
      if (online) {
        unawaited(flush());
      }
    });
    _periodicTimer ??= Timer.periodic(const Duration(seconds: 60), (_) {
      unawaited(flush());
    });
    // Tenta flush inicial.
    unawaited(flush());
  }

  Future<void> stop() async {
    await _connSub?.cancel();
    _connSub = null;
    _periodicTimer?.cancel();
    _periodicTimer = null;
  }

  /// Enfileira um item. Atalho pro repo.
  Future<int> enqueue({
    required String osId,
    required OutboxKind kind,
    required Map<String, dynamic> payload,
    String? filePath,
  }) {
    return _outbox.enqueue(
      osId: osId,
      kind: kind,
      payload: payload,
      filePath: filePath,
    );
  }

  Future<int> pendingCount() => _outbox.pendingCount();

  /// Processa todos os items pendentes. Não-reentrante.
  Future<void> flush() async {
    if (_flushing) return;
    _flushing = true;
    try {
      final items = await _outbox.pending(limit: 50);
      for (final item in items) {
        if (!_shouldAttempt(item)) continue;
        final ok = await _processItem(item);
        if (!ok) break; // network down → para pro proximo ciclo
      }
    } finally {
      _flushing = false;
    }
  }

  bool _shouldAttempt(OutboxItemData item) {
    return shouldAttemptAt(item, DateTime.now());
  }

  /// Retorna `false` se erro foi de rede (devemos parar o flush).
  /// Retorna `true` em sucesso OU erro de validação (4xx — permanente).
  Future<bool> _processItem(OutboxItemData item) async {
    try {
      final kind = OutboxKindString.parse(item.kind);
      switch (kind) {
        case OutboxKind.iniciar:
          await _dio.post(
            '/api/v1/tecnico/me/os/${item.osId}/iniciar',
            data: jsonDecode(item.payloadJson),
          );
          break;
        case OutboxKind.concluir:
          await _dio.post(
            '/api/v1/tecnico/me/os/${item.osId}/concluir',
            data: jsonDecode(item.payloadJson),
          );
          break;
        case OutboxKind.foto:
          final path = item.filePath;
          if (path == null) {
            await _outbox.markAttempt(item.id, 'filePath ausente');
            return true;
          }
          final f = File(path);
          if (!await f.exists()) {
            await _outbox.markAttempt(item.id, 'arquivo nao encontrado: $path');
            return true;
          }
          final form = FormData.fromMap({
            'file': await MultipartFile.fromFile(path, filename: 'foto.jpg'),
          });
          await _dio.post(
            '/api/v1/tecnico/me/os/${item.osId}/foto',
            data: form,
          );
          // Marca enviado ANTES de apagar o arquivo: se o delete falhar
          // (permissao/arquivo em uso), o item nao reenvia o POST duplicado.
          await _outbox.markSent(item.id);
          await _outbox.deleteFileIfExists(path);
          return true;
      }
      await _outbox.markSent(item.id);
      return true;
    } on DioException catch (e) {
      final code = e.response?.statusCode;
      final retryable = isRetryableSyncError(e);
      await _outbox.markAttempt(
        item.id,
        '${e.type.name} status=${code ?? "-"}: ${e.message}',
      );
      if (!retryable) {
        await _outbox.markSent(item.id);
        return true;
      }
      return code != null;
    } catch (e) {
      await _outbox.markAttempt(item.id, e.toString());
      return true;
    }
  }
}

final syncServiceProvider = Provider<SyncService>((ref) {
  final svc = SyncService(ref.watch(apiClientProvider), ref.watch(dbProvider));
  ref.onDispose(svc.stop);
  return svc;
});

/// Stream do count de pendentes — atualiza a cada 5s. Usado pelo badge.
final pendingCountProvider = StreamProvider<int>((ref) async* {
  final svc = ref.watch(syncServiceProvider);
  while (true) {
    yield await svc.pendingCount();
    await Future<void>.delayed(const Duration(seconds: 5));
  }
});
