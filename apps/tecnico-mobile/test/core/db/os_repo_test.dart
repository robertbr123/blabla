import 'dart:convert';

import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/db/database.dart';
import 'package:tecnico_mobile/core/db/os_repo.dart';

AppDatabase testDatabase() => AppDatabase.forTesting(NativeDatabase.memory());

Map<String, dynamic> sampleOs({
  required String status,
}) {
  return {
    'id': 'os-1',
    'codigo': 'OS-001',
    'status': status,
    'problema': 'Sem sinal',
    'endereco': 'Rua A, 100',
    'nome_cliente': 'Cliente Teste',
    'agendamento_at': '2026-05-19T09:00:00Z',
    'criada_em': '2026-05-18T12:00:00Z',
    'concluida_em': null,
  };
}

void main() {
  test('markStartedOptimistic updates payloadJson persisted and status column',
      () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = OsLocalRepo(db);
    await repo.upsertOne(sampleOs(status: 'pendente'));

    await repo.markStartedOptimistic('os-1');

    final cached = await repo.getById('os-1');
    final row = await (db.select(db.osLocal)..where((t) => t.id.equals('os-1')))
        .getSingle();

    expect(cached?['status'], 'em_andamento');
    expect(row.status, 'em_andamento');
    expect(
      (jsonDecode(row.payloadJson) as Map<String, dynamic>)['status'],
      'em_andamento',
    );
  });

  test(
      'markConcludedOptimistic updates payloadJson, status and concluida_em locally',
      () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = OsLocalRepo(db);
    await repo.upsertOne(sampleOs(status: 'em_andamento'));

    await repo.markConcludedOptimistic('os-1', const {'relatorio': 'ok'});

    final cached = await repo.getById('os-1');
    final row = await (db.select(db.osLocal)..where((t) => t.id.equals('os-1')))
        .getSingle();
    final persistedPayload =
        jsonDecode(row.payloadJson) as Map<String, dynamic>;

    expect(cached?['status'], 'concluida');
    expect(cached?['relatorio'], 'ok');
    expect(cached?['concluida_em'], isA<String>());
    expect(DateTime.tryParse(cached!['concluida_em'] as String), isNotNull);
    expect(row.status, 'concluida');
    expect(row.concluidaEm, cached['concluida_em']);
    expect(persistedPayload['status'], 'concluida');
    expect(persistedPayload['relatorio'], 'ok');
    expect(persistedPayload['concluida_em'], cached['concluida_em']);
  });

  test('markConcludedOptimistic does not let payload override forced fields',
      () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = OsLocalRepo(db);
    await repo.upsertOne(sampleOs(status: 'em_andamento'));

    await repo.markConcludedOptimistic('os-1', const {
      'status': 'pendente',
      'concluida_em': null,
      'relatorio': 'ok',
    });

    final cached = await repo.getById('os-1');

    expect(cached?['status'], 'concluida');
    expect(cached?['concluida_em'], isA<String>());
    expect(cached?['relatorio'], 'ok');
  });

  test('upsertAll preserves optimistic status against stale server snapshot',
      () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = OsLocalRepo(db);
    await repo.upsertOne(sampleOs(status: 'pendente'));
    await repo.markStartedOptimistic('os-1');

    await repo.upsertAll([sampleOs(status: 'pendente')]);

    final cached = await repo.getById('os-1');
    expect(cached?['status'], 'em_andamento');
  });

  test('upsertAll keeps fresh server fields while preserving optimistic status',
      () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = OsLocalRepo(db);
    await repo.upsertOne(sampleOs(status: 'pendente'));
    await repo.markStartedOptimistic('os-1');

    final serverSnapshot = sampleOs(status: 'pendente')
      ..['endereco'] = 'Rua Nova, 200'
      ..['problema'] = 'Atualizado pelo servidor';

    await repo.upsertAll([serverSnapshot]);

    final cached = await repo.getById('os-1');
    expect(cached?['status'], 'em_andamento');
    expect(cached?['endereco'], 'Rua Nova, 200');
    expect(cached?['problema'], 'Atualizado pelo servidor');
  });

  test(
      'upsertAll preserves optimistic local payload fields missing from stale server snapshot',
      () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = OsLocalRepo(db);
    await repo.upsertOne(sampleOs(status: 'em_andamento'));
    await repo.markConcludedOptimistic('os-1', const {'relatorio': 'ok'});

    await repo.upsertAll([sampleOs(status: 'em_andamento')]);

    final cached = await repo.getById('os-1');
    expect(cached?['status'], 'concluida');
    expect(cached?['relatorio'], 'ok');
    expect(cached?['concluida_em'], isA<String>());
  });

  test(
      'upsertAll preserves local detail fields when server returns concluded with partial payload',
      () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = OsLocalRepo(db);
    await repo.upsertOne(sampleOs(status: 'em_andamento'));
    await repo.markConcludedOptimistic('os-1', const {'relatorio': 'ok'});

    final serverSnapshot = sampleOs(status: 'concluida')
      ..remove('concluida_em')
      ..['endereco'] = 'Rua Nova, 200';

    await repo.upsertAll([serverSnapshot]);

    final cached = await repo.getById('os-1');
    expect(cached?['status'], 'concluida');
    expect(cached?['relatorio'], 'ok');
    expect(cached?['concluida_em'], isA<String>());
    expect(cached?['endereco'], 'Rua Nova, 200');
  });

  test(
      'upsertAll accepts authoritative concluida_em from server while preserving local detail fields',
      () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = OsLocalRepo(db);
    await repo.upsertOne(sampleOs(status: 'em_andamento'));
    await repo.markConcludedOptimistic('os-1', const {'relatorio': 'ok'});

    final local = await repo.getById('os-1');
    final localConcludedAt = local?['concluida_em'];
    const serverConcludedAt = '2026-05-19T16:30:00Z';
    final serverSnapshot = sampleOs(status: 'concluida')
      ..['concluida_em'] = serverConcludedAt
      ..['endereco'] = 'Rua Final, 999';

    await repo.upsertAll([serverSnapshot]);

    final cached = await repo.getById('os-1');
    final row = await (db.select(db.osLocal)..where((t) => t.id.equals('os-1')))
        .getSingle();
    expect(cached?['status'], 'concluida');
    expect(cached?['relatorio'], 'ok');
    expect(cached?['endereco'], 'Rua Final, 999');
    expect(cached?['concluida_em'], serverConcludedAt);
    expect(cached?['concluida_em'], isNot(localConcludedAt));
    expect(row.concluidaEm, serverConcludedAt);
  });

  test('upsertAll accepts authoritative terminal status from server', () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = OsLocalRepo(db);
    await repo.upsertOne(sampleOs(status: 'em_andamento'));
    await repo.markConcludedOptimistic('os-1', const {'relatorio': 'ok'});

    final serverSnapshot = sampleOs(status: 'cancelada')
      ..['motivo_cancelamento'] = 'Cliente ausente'
      ..['concluida_em'] = null;

    await repo.upsertAll([serverSnapshot]);

    final cached = await repo.getById('os-1');
    expect(cached?['status'], 'cancelada');
    expect(cached?['motivo_cancelamento'], 'Cliente ausente');
  });
}
