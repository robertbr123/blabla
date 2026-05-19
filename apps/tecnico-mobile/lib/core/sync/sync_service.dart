// TODO M-mobile-2: outbox sync — processa OutboxItem pendentes.
//
// Fluxo:
//  1. Connectivity listener: quando rede volta, dispara flush
//  2. Pra cada item ordem FIFO:
//     - kind=iniciar → POST /api/v1/tecnico/me/os/{id}/iniciar
//     - kind=concluir → POST /api/v1/tecnico/me/os/{id}/concluir
//     - kind=foto → multipart POST /api/v1/tecnico/me/os/{id}/foto
//  3. Sucesso → marca sent_at
//  4. Falha 5xx ou network → incrementa attempts, exponential backoff
//  5. 4xx (validação) → marca como erro permanente + alerta ao técnico
//
// Reentrante: idempotency por (os_id, kind, payload_hash) — quando backend
// expor X-Idempotency-Key. Por enquanto, dedup local antes do enqueue.

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../db/database.dart';

class SyncService {
  final Dio _dio;
  final AppDatabase _db;

  SyncService(this._dio, this._db);

  Future<void> flushOutbox() async {
    // TODO implementar — esqueleto pra próximo PR
  }
}

final syncServiceProvider = Provider<SyncService>((ref) {
  return SyncService(ref.watch(apiClientProvider), ref.watch(dbProvider));
});
