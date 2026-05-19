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

  Future<void> clear({required String userId}) {
    return (_db.delete(_db.estoqueLocal)
          ..where((t) => t.userId.equals(userId)))
        .go();
  }
}
