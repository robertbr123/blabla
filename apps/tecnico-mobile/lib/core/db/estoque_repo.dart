import 'dart:convert';

import 'package:drift/drift.dart';

import 'database.dart';

class EstoqueLocalRepo {
  final AppDatabase _db;
  EstoqueLocalRepo(this._db);

  Future<void> replaceAll({
    required String userId,
    required List<Map<String, dynamic>> rows,
  }) async {
    final now = DateTime.now();
    await _db.transaction(() async {
      await clear(userId: userId);
      await _db.batch((batch) {
        for (final row in rows) {
          batch.insert(
            _db.estoqueLocal,
            EstoqueLocalCompanion.insert(
              userId: userId,
              itemId: (row['item_id'] ?? '') as String,
              payloadJson: jsonEncode(row),
              syncedAt: now,
            ),
            mode: InsertMode.insertOrReplace,
          );
        }
      });
    });
  }

  Future<List<Map<String, dynamic>>> listAll({required String userId}) async {
    final rows = await (_db.select(_db.estoqueLocal)
          ..where((t) => t.userId.equals(userId))
          ..orderBy([(t) => OrderingTerm.asc(t.itemId)]))
        .get();
    return rows
        .map((row) => jsonDecode(row.payloadJson) as Map<String, dynamic>)
        .toList();
  }

  Future<DateTime?> lastSyncedAt({required String userId}) async {
    final maxExp = _db.estoqueLocal.syncedAt.max();
    final row = await (_db.selectOnly(_db.estoqueLocal)
          ..addColumns([maxExp])
          ..where(_db.estoqueLocal.userId.equals(userId)))
        .getSingle();
    return row.read(maxExp);
  }

  Future<void> clear({required String userId}) {
    return (_db.delete(_db.estoqueLocal)
          ..where((t) => t.userId.equals(userId)))
        .go();
  }
}
