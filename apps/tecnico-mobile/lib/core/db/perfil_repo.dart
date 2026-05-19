import 'dart:convert';

import 'package:drift/drift.dart';

import 'database.dart';

class PerfilLocalRepo {
  final AppDatabase _db;
  PerfilLocalRepo(this._db);

  Future<void> save(Map<String, dynamic> payload) {
    return _db.into(_db.perfilLocal).insert(
          PerfilLocalCompanion.insert(
            userId: (payload['user_id'] ?? '') as String,
            payloadJson: jsonEncode(payload),
            syncedAt: DateTime.now(),
          ),
          mode: InsertMode.insertOrReplace,
        );
  }

  Future<Map<String, dynamic>?> get({required String userId}) async {
    final row = await (_db.select(_db.perfilLocal)
          ..where((t) => t.userId.equals(userId))
          ..limit(1))
        .getSingleOrNull();
    if (row == null) return null;
    return jsonDecode(row.payloadJson) as Map<String, dynamic>;
  }
}
