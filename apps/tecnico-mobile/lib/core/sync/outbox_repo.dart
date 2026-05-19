import 'dart:convert';
import 'dart:io';

import 'package:drift/drift.dart';

import '../db/database.dart';
import 'outbox_kind.dart';

export 'outbox_kind.dart';

class OutboxRepo {
  final AppDatabase _db;
  OutboxRepo(this._db);

  Future<int> enqueue({
    required String osId,
    required OutboxKind kind,
    required Map<String, dynamic> payload,
    String? filePath,
  }) {
    return _db.into(_db.outboxItem).insert(
          OutboxItemCompanion.insert(
            osId: osId,
            kind: kind.wire,
            payloadJson: jsonEncode(payload),
            filePath: Value(filePath),
          ),
        );
  }

  /// Items pendentes (sent_at IS NULL) em ordem FIFO.
  Future<List<OutboxItemData>> pending({int limit = 50}) {
    return (_db.select(_db.outboxItem)
          ..where((o) => o.sentAt.isNull())
          ..orderBy([(o) => OrderingTerm.asc(o.id)])
          ..limit(limit))
        .get();
  }

  Future<void> markSent(int id) async {
    await (_db.update(_db.outboxItem)..where((o) => o.id.equals(id))).write(
      OutboxItemCompanion(sentAt: Value(DateTime.now())),
    );
  }

  Future<void> markAttempt(int id, String? error) async {
    final row = await (_db.select(_db.outboxItem)..where((o) => o.id.equals(id)))
        .getSingleOrNull();
    if (row == null) return;
    await (_db.update(_db.outboxItem)..where((o) => o.id.equals(id))).write(
      OutboxItemCompanion(
        attempts: Value(row.attempts + 1),
        lastError: Value(error),
        lastAttemptAt: Value(DateTime.now()),
      ),
    );
  }

  Future<int> pendingCount() async {
    final row = await (_db.selectOnly(_db.outboxItem)
          ..addColumns([_db.outboxItem.id.count()])
          ..where(_db.outboxItem.sentAt.isNull()))
        .getSingle();
    return row.read(_db.outboxItem.id.count()) ?? 0;
  }

  Future<void> deleteFileIfExists(String? path) async {
    if (path == null) return;
    final f = File(path);
    if (await f.exists()) {
      await f.delete();
    }
  }
}
