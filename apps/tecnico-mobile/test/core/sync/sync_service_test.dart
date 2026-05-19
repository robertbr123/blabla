import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/sync/sync_service.dart';

void main() {
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
