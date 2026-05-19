import 'package:drift/drift.dart';

/// Cache local da OS (synced com backend).
class OsLocal extends Table {
  TextColumn get id => text()();
  TextColumn get codigo => text()();
  TextColumn get status => text()();
  TextColumn get problema => text()();
  TextColumn get endereco => text()();
  TextColumn get nomeCliente => text().nullable()();
  TextColumn get agendamentoAt => text().nullable()(); // ISO
  TextColumn get criadaEm => text()();
  TextColumn get concluidaEm => text().nullable()();
  TextColumn get payloadJson => text()(); // full DTO pra detalhes
  DateTimeColumn get syncedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

/// Outbox: ações offline (concluir/iniciar/foto) esperando upload.
class OutboxItem extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get osId => text()();
  TextColumn get kind => text()(); // 'iniciar' | 'concluir' | 'foto'
  TextColumn get payloadJson => text()(); // body JSON
  TextColumn get filePath => text().nullable()(); // pra foto
  IntColumn get attempts => integer().withDefault(const Constant(0))();
  TextColumn get lastError => text().nullable()();
  DateTimeColumn get lastAttemptAt => dateTime().nullable()();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get sentAt => dateTime().nullable()();
}

/// Snapshot local do saldo de estoque do tecnico.
class EstoqueLocal extends Table {
  TextColumn get userId => text()();
  TextColumn get itemId => text()();
  TextColumn get payloadJson => text()();
  DateTimeColumn get syncedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {userId, itemId};
}

/// Snapshot local do perfil do tecnico.
class PerfilLocal extends Table {
  TextColumn get userId => text()();
  TextColumn get payloadJson => text()();
  DateTimeColumn get syncedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {userId};
}

/// Cache local de cliente_cadastro (lista + detalhe).
/// userId aqui = tecnico logado (cache por user pra nao misturar dados
/// entre logins no mesmo device).
class ClienteCadastroLocal extends Table {
  TextColumn get userId => text()();
  TextColumn get id => text()();           // uuid do cliente_cadastro
  TextColumn get nome => text()();         // descriptografado
  TextColumn get city => text()();
  TextColumn get planNome => text()();
  TextColumn get payloadJson => text()();  // DTO completo pro detalhe
  DateTimeColumn get syncedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {userId, id};
}
