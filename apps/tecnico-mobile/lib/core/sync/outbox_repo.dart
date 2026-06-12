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
    final row = await (_db.select(_db.outboxItem)
          ..where((o) => o.id.equals(id)))
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
    final countExp = _db.outboxItem.id.count();
    final row = await (_db.selectOnly(_db.outboxItem)
          ..addColumns([countExp])
          ..where(_db.outboxItem.sentAt.isNull()))
        .getSingle();
    return row.read(countExp) ?? 0;
  }

  /// Stream reativo do count de pendentes — emite a cada write na tabela.
  Stream<int> watchPendingCount() {
    final countExp = _db.outboxItem.id.count();
    final query = _db.selectOnly(_db.outboxItem)
      ..addColumns([countExp])
      ..where(_db.outboxItem.sentAt.isNull());
    return query.map((row) => row.read(countExp) ?? 0).watchSingle();
  }

  Future<void> clear() async {
    final rows = await _db.select(_db.outboxItem).get();
    for (final row in rows) {
      await deleteFileIfExists(row.filePath);
    }
    await _db.delete(_db.outboxItem).go();
  }

  Future<void> deleteFileIfExists(String? path) async {
    if (path == null) return;
    final f = File(path);
    if (await f.exists()) {
      await f.delete();
    }
  }
}
