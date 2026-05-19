import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/db/database.dart';
import 'package:tecnico_mobile/core/db/estoque_repo.dart';
import 'package:tecnico_mobile/core/db/perfil_repo.dart';

AppDatabase testDatabase() => AppDatabase.forTesting(NativeDatabase.memory());

void main() {
  test('estoque repo round-trips cached rows', () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = EstoqueLocalRepo(db);

    await repo.replaceAll(
      userId: 'u1',
      rows: [
        {
          'item_id': '1',
          'sku': 'CABO',
          'nome': 'Cabo',
          'categoria': 'Rede',
          'serializado': false,
          'saldo': 3,
        },
      ],
    );

    final rows = await repo.listAll(userId: 'u1');
    expect(rows.single['sku'], 'CABO');
  });

  test('perfil repo returns cached snapshot for requested user id', () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = PerfilLocalRepo(db);

    await repo.save({
      'user_id': 'u1',
      'email': 'tecnico@acme.com',
      'nome': 'Tecnico Teste',
      'estatisticas': {
        'os_pendentes': 1,
        'os_em_andamento': 0,
        'os_concluidas_mes': 2,
      },
    });

    await repo.save({
      'user_id': 'u2',
      'email': 'outra@acme.com',
      'nome': 'Outra Pessoa',
      'estatisticas': {
        'os_pendentes': 9,
        'os_em_andamento': 4,
        'os_concluidas_mes': 1,
      },
    });

    final row = await repo.get(userId: 'u1');
    expect(row?['nome'], 'Tecnico Teste');
  });

  test('estoque repo clear removes only requested user snapshot', () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = EstoqueLocalRepo(db);

    await repo.replaceAll(
      userId: 'u1',
      rows: [
        {
          'item_id': '1',
          'sku': 'CABO',
          'nome': 'Cabo',
          'categoria': 'Rede',
          'serializado': false,
          'saldo': 3,
        },
      ],
    );
    await repo.replaceAll(
      userId: 'u2',
      rows: [
        {
          'item_id': '9',
          'sku': 'FIBRA',
          'nome': 'Fibra',
          'categoria': 'Rede',
          'serializado': false,
          'saldo': 7,
        },
      ],
    );

    await repo.clear(userId: 'u1');

    expect(await repo.listAll(userId: 'u1'), isEmpty);
    expect((await repo.listAll(userId: 'u2')).single['sku'], 'FIBRA');
  });

  test('estoque repo keeps snapshots isolated when multiple users coexist', () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = EstoqueLocalRepo(db);

    await repo.replaceAll(
      userId: 'u1',
      rows: [
        {
          'item_id': '1',
          'sku': 'CABO',
          'nome': 'Cabo',
          'categoria': 'Rede',
          'serializado': false,
          'saldo': 3,
        },
      ],
    );
    await repo.replaceAll(
      userId: 'u2',
      rows: [
        {
          'item_id': '2',
          'sku': 'FIBRA',
          'nome': 'Fibra',
          'categoria': 'Rede',
          'serializado': false,
          'saldo': 7,
        },
      ],
    );

    final rows = await repo.listAll(userId: 'u1');

    expect(rows, hasLength(1));
    expect(rows.single['sku'], 'CABO');
    expect(rows.single['item_id'], '1');
  });
}
