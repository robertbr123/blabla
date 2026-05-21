import 'package:drift/native.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/db/database.dart';
import 'package:tecnico_mobile/core/sync/outbox_repo.dart';
import 'package:tecnico_mobile/core/sync/outbox_kind.dart';
import 'package:tecnico_mobile/core/sync/sync_service.dart';

AppDatabase testDatabase() => AppDatabase.forTesting(NativeDatabase.memory());

class _PermanentFailureAdapter implements HttpClientAdapter {
  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<List<int>>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    throw DioException(
      requestOptions: options,
      response: Response(
        requestOptions: options,
        statusCode: 400,
        data: {'detail': 'invalid state'},
      ),
      type: DioExceptionType.badResponse,
    );
  }
}

Dio _permanentFailureDio() {
  final dio = Dio();
  dio.httpClientAdapter = _PermanentFailureAdapter();
  return dio;
}

void main() {
  test('markAttempt increments attempts and updates lastAttemptAt', () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = OutboxRepo(db);
    final id = await repo.enqueue(
      osId: 'os-1',
      kind: OutboxKind.iniciar,
      payload: const {'lat': 1},
    );

    await repo.markAttempt(id, 'timeout');

    final item = (await repo.pending()).single;
    expect(item.attempts, 1);
    expect(item.lastError, 'timeout');
    expect(item.lastAttemptAt, isNotNull);
  });

  test('backoff uses lastAttemptAt when present', () {
    final now = DateTime(2026, 5, 19, 12);
    final createdAt = now.subtract(const Duration(hours: 5));
    final lastAttemptAt = now.subtract(const Duration(seconds: 5));

    final next = computeNextRetryAt(
      attempts: 2,
      createdAt: createdAt,
      lastAttemptAt: lastAttemptAt,
    );

    expect(next, lastAttemptAt.add(const Duration(seconds: 4)));
  });

  test('backoff falls back to createdAt when item never retried', () {
    final createdAt = DateTime(2026, 5, 19, 12);

    final next = computeNextRetryAt(
      attempts: 3,
      createdAt: createdAt,
      lastAttemptAt: null,
    );

    expect(next, createdAt.add(const Duration(seconds: 8)));
  });

  test('shouldAttempt waits until retry window after last attempt', () {
    final now = DateTime(2026, 5, 19, 12, 0, 10);
    final item = OutboxItemData(
      id: 1,
      osId: 'os-1',
      kind: OutboxKind.iniciar.wire,
      payloadJson: '{}',
      attempts: 2,
      lastAttemptAt: DateTime(2026, 5, 19, 12, 0, 8),
      createdAt: DateTime(2026, 5, 19, 11),
    );

    expect(shouldAttemptAt(item, now), isFalse);
  });

  test('shouldAttempt allows retry exactly at next retry instant', () {
    final now = DateTime(2026, 5, 19, 12, 0, 12);
    final item = OutboxItemData(
      id: 1,
      osId: 'os-1',
      kind: OutboxKind.iniciar.wire,
      payloadJson: '{}',
      attempts: 2,
      lastAttemptAt: DateTime(2026, 5, 19, 12, 0, 8),
      createdAt: DateTime(2026, 5, 19, 11),
    );

    expect(shouldAttemptAt(item, now), isTrue);
  });

  test('isRetryableSyncError only retries transient dio failures', () {
    final request = RequestOptions(path: '/os');

    expect(
      isRetryableSyncError(
        DioException(
          requestOptions: request,
          type: DioExceptionType.connectionError,
        ),
      ),
      isTrue,
    );
    expect(
      isRetryableSyncError(
        DioException(
          requestOptions: request,
          response: Response(
            requestOptions: request,
            statusCode: 500,
          ),
          type: DioExceptionType.badResponse,
        ),
      ),
      isTrue,
    );
    expect(
      isRetryableSyncError(
        DioException(
          requestOptions: request,
          response: Response(
            requestOptions: request,
            statusCode: 400,
          ),
          type: DioExceptionType.badResponse,
        ),
      ),
      isFalse,
    );
  });

  test('flush finalizes permanent 400 outbox item instead of retrying forever',
      () async {
    final db = testDatabase();
    addTearDown(db.close);

    final svc = SyncService(_permanentFailureDio(), db);
    final repo = OutboxRepo(db);

    final id = await repo.enqueue(
      osId: 'os-1',
      kind: OutboxKind.iniciar,
      payload: const {'lat': 1},
    );

    await svc.flush();

    expect(await repo.pendingCount(), 0);

    final row = await (db.select(db.outboxItem)..where((t) => t.id.equals(id)))
        .getSingle();
    expect(row.attempts, 1);
    expect(row.lastError, contains('status=400'));
    expect(row.sentAt, isNotNull);
  });
}
