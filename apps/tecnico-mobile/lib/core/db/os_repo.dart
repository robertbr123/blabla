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
    await _db.transaction(() async {
      for (final os in osList) {
        final incoming = Map<String, dynamic>.from(os);
        final merged = await _mergeWithLocalOptimisticState(incoming);
        await _db.into(_db.osLocal).insert(
              OsLocalCompanion.insert(
                id: merged['id'] as String,
                codigo: (merged['codigo'] ?? '') as String,
                status: (merged['status'] ?? '') as String,
                problema: (merged['problema'] ?? '') as String,
                endereco: (merged['endereco'] ?? '') as String,
                nomeCliente: Value(merged['nome_cliente'] as String?),
                agendamentoAt: Value(merged['agendamento_at'] as String?),
                criadaEm: (merged['criada_em'] ?? '') as String,
                concluidaEm: Value(merged['concluida_em'] as String?),
                payloadJson: jsonEncode(merged),
                syncedAt: now,
              ),
              mode: InsertMode.insertOrReplace,
            );
      }
    });
  }

  /// Upsert de uma OS individual (apos endpoint de detalhe).
  Future<void> upsertOne(Map<String, dynamic> os) => upsertAll([os]);

  /// Reconcilia a lista local com a vinda da API: faz upsert das presentes
  /// e DELETA as que sumiram (foram excluidas pelo admin no dashboard).
  /// Chamado pelo refresh da lista — nao pelo upsert de detalhe.
  Future<void> reconcileWithServer(List<Map<String, dynamic>> serverList) async {
    final serverIds = serverList.map((o) => o['id'] as String).toSet();
    await upsertAll(serverList);
    // Apaga locais que nao estao mais na resposta do servidor.
    await (_db.delete(_db.osLocal)
          ..where((t) => t.id.isNotIn(serverIds.toList())))
        .go();
  }

  /// Lista todas as OS cacheadas (ordenadas mais recentes primeiro).
  Future<List<Map<String, dynamic>>> listAll() async {
    final rows = await (_db.select(_db.osLocal)
          ..orderBy([(t) => OrderingTerm.desc(t.syncedAt)]))
        .get();
    return rows
        .map((r) => jsonDecode(r.payloadJson) as Map<String, dynamic>)
        .toList();
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
    final row = await (_db.select(_db.osLocal)..where((t) => t.id.equals(id)))
        .getSingleOrNull();
    if (row == null) return null;
    return jsonDecode(row.payloadJson) as Map<String, dynamic>;
  }

  Future<void> markStartedOptimistic(String id) async {
    final row = await getById(id);
    if (row == null) return;

    row['status'] = 'em_andamento';
    await upsertOne(row);
  }

  Future<void> markConcludedOptimistic(
    String id,
    Map<String, dynamic> payload,
  ) async {
    final row = await getById(id);
    if (row == null) return;

    final concludedAt = DateTime.now().toIso8601String();
    row.addAll(payload);
    row['status'] = 'concluida';
    row['concluida_em'] = concludedAt;
    await upsertOne(row);
  }

  Future<Map<String, dynamic>> _mergeWithLocalOptimisticState(
    Map<String, dynamic> incoming,
  ) async {
    final id = incoming['id'] as String?;
    if (id == null || id.isEmpty) return incoming;

    final current = await getById(id);
    if (current == null) return incoming;

    final currentStatus = current['status']?.toString() ?? '';
    final incomingStatus = incoming['status']?.toString() ?? '';
    final shouldPreserveStatus = _shouldPreserveLocalStatus(
      currentStatus: currentStatus,
      incomingStatus: incomingStatus,
    );

    if (shouldPreserveStatus ||
        _shouldMergeConcludedPayload(
          currentStatus: currentStatus,
          incomingStatus: incomingStatus,
        )) {
      final merged = <String, dynamic>{...current, ...incoming};
      if (shouldPreserveStatus) {
        merged['status'] = currentStatus;
      }
      if (_shouldPreserveLocalConcludedAt(
        currentStatus: currentStatus,
        incomingConcludedAt: incoming['concluida_em'],
      )) {
        merged['concluida_em'] = current['concluida_em'];
      }
      return merged;
    }

    return incoming;
  }

  bool _shouldPreserveLocalStatus({
    required String currentStatus,
    required String incomingStatus,
  }) {
    final currentOrder = _statusOrder(currentStatus);
    final incomingOrder = _statusOrder(incomingStatus);
    if (currentOrder == null || incomingOrder == null) {
      return false;
    }

    return currentOrder > incomingOrder;
  }

  bool _shouldMergeConcludedPayload({
    required String currentStatus,
    required String incomingStatus,
  }) {
    return currentStatus == 'concluida' && incomingStatus == 'concluida';
  }

  bool _shouldPreserveLocalConcludedAt({
    required String currentStatus,
    required Object? incomingConcludedAt,
  }) {
    if (currentStatus != 'concluida') {
      return false;
    }

    final incomingValue = incomingConcludedAt?.toString().trim() ?? '';
    return incomingValue.isEmpty;
  }

  int? _statusOrder(String status) {
    switch (status) {
      case 'pendente':
        return 0;
      case 'em_andamento':
        return 1;
      case 'concluida':
        return 2;
      default:
        return null;
    }
  }

  /// Apaga OS cacheada — usar quando user desloga.
  Future<void> clear() async {
    await _db.delete(_db.osLocal).go();
  }
}
