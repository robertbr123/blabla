import 'dart:convert';

import 'package:drift/drift.dart';

import 'database.dart';

/// Cache local de clientes cadastrados (lista + detalhe).
/// Multi-user: cada user tem o proprio snapshot (chave composta userId+id).
class ClienteCadastroLocalRepo {
  final AppDatabase _db;
  ClienteCadastroLocalRepo(this._db);

  /// Substitui toda a lista do user pelo snapshot vindo da API.
  Future<void> replaceAll({
    required String userId,
    required List<Map<String, dynamic>> rows,
  }) async {
    await _db.transaction(() async {
      await (_db.delete(_db.clienteCadastroLocal)
            ..where((t) => t.userId.equals(userId)))
          .go();
      if (rows.isEmpty) return;
      final now = DateTime.now();
      await _db.batch((batch) {
        for (final row in rows) {
          batch.insert(
            _db.clienteCadastroLocal,
            ClienteCadastroLocalCompanion.insert(
              userId: userId,
              id: (row['id'] ?? '') as String,
              nome: (row['nome'] ?? '') as String,
              city: (row['city'] ?? '') as String,
              planNome: (row['plan_nome'] ?? '') as String,
              payloadJson: jsonEncode(row),
              syncedAt: now,
            ),
            mode: InsertMode.insertOrReplace,
          );
        }
      });
    });
  }

  /// Upsert de UM cliente (apos GET de detalhe — payload mais completo).
  Future<void> upsertOne({
    required String userId,
    required Map<String, dynamic> row,
  }) async {
    await _db.into(_db.clienteCadastroLocal).insert(
          ClienteCadastroLocalCompanion.insert(
            userId: userId,
            id: (row['id'] ?? '') as String,
            nome: (row['nome'] ?? '') as String,
            city: (row['city'] ?? '') as String,
            planNome: (row['plan_nome'] ?? '') as String,
            payloadJson: jsonEncode(row),
            syncedAt: DateTime.now(),
          ),
          mode: InsertMode.insertOrReplace,
        );
  }

  Future<List<Map<String, dynamic>>> listAll({
    required String userId,
  }) async {
    final rows = await (_db.select(_db.clienteCadastroLocal)
          ..where((t) => t.userId.equals(userId))
          ..orderBy([(t) => OrderingTerm.desc(t.syncedAt)]))
        .get();
    return rows
        .map((r) => jsonDecode(r.payloadJson) as Map<String, dynamic>)
        .toList();
  }

  Future<Map<String, dynamic>?> get({
    required String userId,
    required String id,
  }) async {
    final row = await (_db.select(_db.clienteCadastroLocal)
          ..where((t) => t.userId.equals(userId) & t.id.equals(id)))
        .getSingleOrNull();
    if (row == null) return null;
    return jsonDecode(row.payloadJson) as Map<String, dynamic>;
  }

  Future<void> clear({required String userId}) async {
    await (_db.delete(_db.clienteCadastroLocal)
          ..where((t) => t.userId.equals(userId)))
        .go();
  }
}
