import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/db/database.dart';
import 'package:tecnico_mobile/core/sync/outbox_repo.dart';
import 'package:tecnico_mobile/core/sync/outbox_kind.dart';
import 'package:tecnico_mobile/core/sync/sync_service.dart';

AppDatabase testDatabase() => AppDatabase.forTesting(NativeDatabase.memory());

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
}
