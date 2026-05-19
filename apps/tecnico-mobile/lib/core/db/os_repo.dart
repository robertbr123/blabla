import 'dart:convert';

import 'package:drift/drift.dart';

import 'database.dart';

/// Cache local de OS atribuidas ao tecnico. Read-through:
///   - UI le do cache (instantaneo)
///   - Background fetch da API e atualiza o cache
///   - Se offline, UI continua valida com o ultimo snapshot
class OsLocalRepo {
  final AppDatabase _db;
  OsLocalRepo(this._db);

  /// Upserts em lote a partir da lista vinda da API.
  Future<void> upsertAll(List<Map<String, dynamic>> osList) async {
    final now = DateTime.now();
    await _db.batch((batch) {
      for (final os in osList) {
        batch.insert(
          _db.osLocal,
          OsLocalCompanion.insert(
            id: os['id'] as String,
            codigo: (os['codigo'] ?? '') as String,
            status: (os['status'] ?? '') as String,
            problema: (os['problema'] ?? '') as String,
            endereco: (os['endereco'] ?? '') as String,
            nomeCliente: Value(os['nome_cliente'] as String?),
            agendamentoAt: Value(os['agendamento_at'] as String?),
            criadaEm: (os['criada_em'] ?? '') as String,
            concluidaEm: Value(os['concluida_em'] as String?),
            payloadJson: jsonEncode(os),
            syncedAt: now,
          ),
          mode: InsertMode.insertOrReplace,
        );
      }
    });
  }

  /// Upsert de uma OS individual (apos endpoint de detalhe).
  Future<void> upsertOne(Map<String, dynamic> os) =>
      upsertAll([os]);

  /// Lista todas as OS cacheadas (ordenadas mais recentes primeiro).
  Future<List<Map<String, dynamic>>> listAll() async {
    final rows = await (_db.select(_db.osLocal)
          ..orderBy([(t) => OrderingTerm.desc(t.syncedAt)]))
        .get();
    return rows.map((r) => jsonDecode(r.payloadJson) as Map<String, dynamic>).toList();
  }

  /// Stream da lista (atualiza em tempo real quando upsert).
  Stream<List<Map<String, dynamic>>> watchAll() {
    return (_db.select(_db.osLocal)
          ..orderBy([(t) => OrderingTerm.desc(t.syncedAt)]))
        .watch()
        .map(
          (rows) => rows
              .map((r) => jsonDecode(r.payloadJson) as Map<String, dynamic>)
              .toList(),
        );
  }

  /// Detalhe cacheado por id.
  Future<Map<String, dynamic>?> getById(String id) async {
    final row =
        await (_db.select(_db.osLocal)..where((t) => t.id.equals(id)))
            .getSingleOrNull();
    if (row == null) return null;
    return jsonDecode(row.payloadJson) as Map<String, dynamic>;
  }

  /// Apaga OS cacheada — usar quando user desloga.
  Future<void> clear() async {
    await _db.delete(_db.osLocal).go();
  }
}
