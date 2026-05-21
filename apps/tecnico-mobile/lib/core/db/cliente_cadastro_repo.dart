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
          final normalized = normalizeClienteCachedPayload(row, now: now);
          batch.insert(
            _db.clienteCadastroLocal,
            ClienteCadastroLocalCompanion.insert(
              userId: userId,
              id: (normalized['id'] ?? '') as String,
              nome: (normalized['nome'] ?? '') as String,
              city: (normalized['city'] ?? '') as String,
              planNome: (normalized['plan_nome'] ?? '') as String,
              payloadJson: jsonEncode(normalized),
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
    final normalized = normalizeClienteCachedPayload(row);
    await _db.into(_db.clienteCadastroLocal).insert(
          ClienteCadastroLocalCompanion.insert(
            userId: userId,
            id: (normalized['id'] ?? '') as String,
            nome: (normalized['nome'] ?? '') as String,
            city: (normalized['city'] ?? '') as String,
            planNome: (normalized['plan_nome'] ?? '') as String,
            payloadJson: jsonEncode(normalized),
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
        .map(
          (r) => normalizeClienteCachedPayload(
            jsonDecode(r.payloadJson) as Map<String, dynamic>,
            now: r.syncedAt,
          ),
        )
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
    return normalizeClienteCachedPayload(
      jsonDecode(row.payloadJson) as Map<String, dynamic>,
      now: row.syncedAt,
    );
  }

  Future<void> clear({required String userId}) async {
    await (_db.delete(_db.clienteCadastroLocal)
          ..where((t) => t.userId.equals(userId)))
        .go();
  }
}

Map<String, dynamic> normalizeClienteCachedPayload(
  Map<String, dynamic> row, {
  DateTime? now,
}) {
  final reference = now ?? DateTime.now();
  final createdAt = _readIsoString(
    row,
    ['created_at', 'registration_date', 'updated_at'],
    fallback: reference.toUtc().toIso8601String(),
  );
  final updatedAt = _readIsoString(
    row,
    ['updated_at', 'created_at', 'registration_date'],
    fallback: createdAt,
  );
  final registrationDate = _readIsoString(
    row,
    ['registration_date', 'created_at', 'updated_at'],
    fallback: createdAt,
  );

  final normalized = <String, dynamic>{
    'id': '',
    'cpf': '',
    'nome': '',
    'dob': '1900-01-01T00:00:00Z',
    'telefone': '',
    'email': null,
    'cep': null,
    'address': '',
    'number': '',
    'complement': null,
    'neighborhood': null,
    'city': '',
    'state': null,
    'plan_id': null,
    'plan_nome': '',
    'pppoe_user': null,
    'pppoe_pass': null,
    'due_date': 1,
    'installer_user_id': null,
    'installer_nome': '',
    'serial': null,
    'contrato': null,
    'observation': null,
    'latitude': null,
    'longitude': null,
    'location_accuracy': null,
    'fotos': const <Map<String, dynamic>>[],
    'registration_date': registrationDate,
    'sgp_synced_at': null,
    'sgp_id': null,
    'created_at': createdAt,
    'updated_at': updatedAt,
    ...row,
  };
  normalized['created_at'] = createdAt;
  normalized['updated_at'] = updatedAt;
  normalized['registration_date'] = registrationDate;
  return normalized;
}

String _readIsoString(
  Map<String, dynamic> row,
  List<String> keys, {
  required String fallback,
}) {
  for (final key in keys) {
    final value = row[key]?.toString().trim();
    if (value != null && value.isNotEmpty) {
      return value;
    }
  }
  return fallback;
}
