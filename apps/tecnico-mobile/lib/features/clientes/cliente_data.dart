import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/auth/auth_storage.dart';
import '../../core/db/cliente_cadastro_repo.dart';
import '../../core/db/database.dart';

class ClienteListItem {
  final String id;
  final String cpf;
  final String nome;
  final String address;
  final String number;
  final String? neighborhood;
  final String city;
  final String planNome;
  final String installerNome;
  final DateTime? sgpSyncedAt;
  final String? sgpId;
  final DateTime createdAt;

  ClienteListItem({
    required this.id,
    required this.cpf,
    required this.nome,
    required this.address,
    required this.number,
    required this.neighborhood,
    required this.city,
    required this.planNome,
    required this.installerNome,
    required this.sgpSyncedAt,
    required this.sgpId,
    required this.createdAt,
  });

  factory ClienteListItem.fromJson(Map<String, dynamic> j) => ClienteListItem(
        id: j['id'] as String,
        cpf: (j['cpf'] ?? '') as String,
        nome: (j['nome'] ?? '') as String,
        address: (j['address'] ?? '') as String,
        number: (j['number'] ?? '') as String,
        neighborhood: j['neighborhood'] as String?,
        city: (j['city'] ?? '') as String,
        planNome: (j['plan_nome'] ?? '') as String,
        installerNome: (j['installer_nome'] ?? '') as String,
        sgpSyncedAt: j['sgp_synced_at'] != null
            ? DateTime.tryParse(j['sgp_synced_at'] as String)
            : null,
        sgpId: j['sgp_id'] as String?,
        createdAt: DateTime.parse(j['created_at'] as String),
      );
}

class ClienteCampo {
  final String id;
  final String cpf;
  final String nome;
  final DateTime dob;
  final String telefone;
  final String? email;
  final String? cep;
  final String address;
  final String number;
  final String? complement;
  final String? neighborhood;
  final String city;
  final String? state;
  final int? planId;
  final String planNome;
  final String? pppoeUser;
  final String? pppoePass;
  final int dueDate;
  final String? installerUserId;
  final String installerNome;
  final String? serial;
  final String? contrato;
  final String? observation;
  final double? latitude;
  final double? longitude;
  final double? locationAccuracy;
  final List<Map<String, dynamic>>? fotos;
  final DateTime registrationDate;
  final DateTime? sgpSyncedAt;
  final String? sgpId;
  final DateTime createdAt;
  final DateTime updatedAt;

  ClienteCampo({
    required this.id,
    required this.cpf,
    required this.nome,
    required this.dob,
    required this.telefone,
    required this.email,
    required this.cep,
    required this.address,
    required this.number,
    required this.complement,
    required this.neighborhood,
    required this.city,
    required this.state,
    required this.planId,
    required this.planNome,
    required this.pppoeUser,
    required this.pppoePass,
    required this.dueDate,
    required this.installerUserId,
    required this.installerNome,
    required this.serial,
    required this.contrato,
    required this.observation,
    required this.latitude,
    required this.longitude,
    required this.locationAccuracy,
    required this.fotos,
    required this.registrationDate,
    required this.sgpSyncedAt,
    required this.sgpId,
    required this.createdAt,
    required this.updatedAt,
  });

  factory ClienteCampo.fromJson(Map<String, dynamic> j) => ClienteCampo(
        id: j['id'] as String,
        cpf: (j['cpf'] ?? '') as String,
        nome: (j['nome'] ?? '') as String,
        dob: DateTime.parse(j['dob'] as String),
        telefone: (j['telefone'] ?? '') as String,
        email: j['email'] as String?,
        cep: j['cep'] as String?,
        address: (j['address'] ?? '') as String,
        number: (j['number'] ?? '') as String,
        complement: j['complement'] as String?,
        neighborhood: j['neighborhood'] as String?,
        city: (j['city'] ?? '') as String,
        state: j['state'] as String?,
        planId: j['plan_id'] as int?,
        planNome: (j['plan_nome'] ?? '') as String,
        pppoeUser: j['pppoe_user'] as String?,
        pppoePass: j['pppoe_pass'] as String?,
        dueDate: (j['due_date'] ?? 1) as int,
        installerUserId: j['installer_user_id'] as String?,
        installerNome: (j['installer_nome'] ?? '') as String,
        serial: j['serial'] as String?,
        contrato: j['contrato'] as String?,
        observation: j['observation'] as String?,
        latitude: (j['latitude'] as num?)?.toDouble(),
        longitude: (j['longitude'] as num?)?.toDouble(),
        locationAccuracy: (j['location_accuracy'] as num?)?.toDouble(),
        fotos: (j['fotos'] as List?)
            ?.cast<Map>()
            .map((m) => m.cast<String, dynamic>())
            .toList(),
        registrationDate: DateTime.parse(j['registration_date'] as String),
        sgpSyncedAt: j['sgp_synced_at'] != null
            ? DateTime.tryParse(j['sgp_synced_at'] as String)
            : null,
        sgpId: j['sgp_id'] as String?,
        createdAt: DateTime.parse(j['created_at'] as String),
        updatedAt: DateTime.parse(j['updated_at'] as String),
      );
}

class ClienteOsHistorico {
  final String id;
  final String codigo;
  final String status;
  final String problema;
  final DateTime? criadaEm;
  final DateTime? concluidaEm;

  ClienteOsHistorico({
    required this.id,
    required this.codigo,
    required this.status,
    required this.problema,
    required this.criadaEm,
    required this.concluidaEm,
  });

  factory ClienteOsHistorico.fromJson(Map<String, dynamic> j) =>
      ClienteOsHistorico(
        id: j['id'] as String,
        codigo: (j['codigo'] ?? '') as String,
        status: (j['status'] ?? '') as String,
        problema: (j['problema'] ?? '') as String,
        criadaEm: j['criada_em'] != null
            ? DateTime.tryParse(j['criada_em'] as String)
            : null,
        concluidaEm: j['concluida_em'] != null
            ? DateTime.tryParse(j['concluida_em'] as String)
            : null,
      );
}

/// Filtros da listagem
class ClienteListFilter {
  final String? q;
  final String? city;
  final String? sgpStatus; // 'synced' | 'pending'

  const ClienteListFilter({this.q, this.city, this.sgpStatus});

  String toQueryString() {
    final parts = <String>[];
    if (q != null && q!.trim().isNotEmpty)
      parts.add('q=${Uri.encodeQueryComponent(q!.trim())}');
    if (city != null && city!.trim().isNotEmpty) {
      parts.add('city=${Uri.encodeQueryComponent(city!.trim())}');
    }
    if (sgpStatus != null) parts.add('sgp_status=$sgpStatus');
    return parts.join('&');
  }
}

final clienteListFilterProvider =
    StateProvider<ClienteListFilter>((ref) => const ClienteListFilter());

/// Lista paginada (online — Fase 9 adiciona cache Drift).
class ClienteListPage {
  final List<ClienteListItem> items;
  final String? nextCursor;
  ClienteListPage({required this.items, this.nextCursor});
}

final clienteCadastroRepoProvider = Provider<ClienteCadastroLocalRepo>(
  (ref) => ClienteCadastroLocalRepo(ref.watch(dbProvider)),
);

final clienteReadUserIdProvider = Provider<Future<String?> Function()>((ref) {
  return readUserId;
});

/// Lista cache-first:
/// 1. Sem filtro → retorna cache imediatamente e refaz fetch em background
/// 2. Com filtro de busca → vai direto na API (cache so guarda snapshot full)
/// 3. Fallback pro cache quando API falha
final clientesListProvider =
    FutureProvider.autoDispose<ClienteListPage>((ref) async {
  final filter = ref.watch(clienteListFilterProvider);
  final dio = ref.watch(apiClientProvider);
  final repo = ref.watch(clienteCadastroRepoProvider);
  final readCurrentUserId = ref.watch(clienteReadUserIdProvider);
  final userId = await readCurrentUserId();

  final qs = filter.toQueryString();
  final url = '/api/v1/clientes-campo${qs.isNotEmpty ? '?$qs' : ''}';

  try {
    final r = await dio.get(url);
    final raw = r.data as Map<String, dynamic>;
    final items = (raw['items'] as List? ?? const [])
        .cast<Map>()
        .map((m) => ClienteListItem.fromJson(m.cast<String, dynamic>()))
        .toList();

    // So cacheia quando nao tem filtro — cache representa "tudo".
    if (qs.isEmpty && userId != null && userId.isNotEmpty) {
      final rows = (raw['items'] as List? ?? const [])
          .cast<Map>()
          .map((m) => m.cast<String, dynamic>())
          .toList();
      await repo.replaceAll(userId: userId, rows: rows);
    }
    return ClienteListPage(
      items: items,
      nextCursor: raw['next_cursor'] as String?,
    );
  } on DioException catch (e) {
    if (!_isNetworkError(e) || userId == null || userId.isEmpty) {
      rethrow;
    }
    // Fallback offline: usa cache local (ignora filtro de servidor —
    // aplica busca client-side no caminho de cima quando online).
    final cached = await repo.listAll(userId: userId);
    if (cached.isEmpty) {
      rethrow;
    }
    final q = (filter.q ?? '').toLowerCase();
    final filtered = cached.where((row) {
      if (q.isEmpty) return true;
      final nome = (row['nome'] ?? '').toString().toLowerCase();
      final city = (row['city'] ?? '').toString().toLowerCase();
      final address = (row['address'] ?? '').toString().toLowerCase();
      return nome.contains(q) || city.contains(q) || address.contains(q);
    }).toList();
    return ClienteListPage(
      items: filtered.map((m) => ClienteListItem.fromJson(m)).toList(),
      nextCursor: null,
    );
  }
});

/// Detalhe cache-first.
final clienteDetailProvider =
    FutureProvider.autoDispose.family<ClienteCampo, String>((ref, id) async {
  final dio = ref.watch(apiClientProvider);
  final repo = ref.watch(clienteCadastroRepoProvider);
  final userId = await readUserId();

  try {
    final r = await dio.get('/api/v1/clientes-campo/$id');
    final raw = (r.data as Map).cast<String, dynamic>();
    if (userId != null && userId.isNotEmpty) {
      await repo.upsertOne(userId: userId, row: raw);
    }
    return ClienteCampo.fromJson(raw);
  } on DioException catch (e) {
    if (!_isNetworkError(e) || userId == null || userId.isEmpty) {
      rethrow;
    }
    final cached = await repo.get(userId: userId, id: id);
    if (cached != null) {
      return ClienteCampo.fromJson(cached);
    }
    rethrow;
  }
});

bool _isNetworkError(DioException e) {
  return e.type == DioExceptionType.connectionError ||
      e.type == DioExceptionType.connectionTimeout ||
      e.type == DioExceptionType.sendTimeout ||
      e.type == DioExceptionType.receiveTimeout;
}

class MaterialUsado {
  final String movimentoId;
  final String itemId;
  final String sku;
  final String nome;
  final String categoria;
  final bool serializado;
  final int quantidade;
  final String? serial;
  final DateTime criadoEm;
  final String? observacao;

  MaterialUsado({
    required this.movimentoId,
    required this.itemId,
    required this.sku,
    required this.nome,
    required this.categoria,
    required this.serializado,
    required this.quantidade,
    required this.serial,
    required this.criadoEm,
    required this.observacao,
  });

  factory MaterialUsado.fromJson(Map<String, dynamic> j) => MaterialUsado(
        movimentoId: j['movimento_id'] as String,
        itemId: j['item_id'] as String,
        sku: (j['sku'] ?? '') as String,
        nome: (j['nome'] ?? '') as String,
        categoria: (j['categoria'] ?? '') as String,
        serializado: (j['serializado'] ?? false) as bool,
        quantidade: (j['quantidade'] as num).toInt(),
        serial: j['serial'] as String?,
        criadoEm: DateTime.parse(j['criado_em'] as String),
        observacao: j['observacao'] as String?,
      );
}

final clienteMateriaisProvider = FutureProvider.autoDispose
    .family<List<MaterialUsado>, String>((ref, id) async {
  final dio = ref.watch(apiClientProvider);
  try {
    final r = await dio.get('/api/v1/clientes-campo/$id/materiais');
    final raw = r.data as List? ?? const [];
    return raw
        .cast<Map>()
        .map((m) => MaterialUsado.fromJson(m.cast<String, dynamic>()))
        .toList();
  } on DioException {
    return const <MaterialUsado>[];
  }
});

/// Histórico de OS por CPF (cruza com Cliente SGP no backend).
final clienteOsHistoricoProvider = FutureProvider.autoDispose
    .family<List<ClienteOsHistorico>, String>((ref, id) async {
  final dio = ref.watch(apiClientProvider);
  try {
    final r = await dio.get('/api/v1/clientes-campo/$id/ordens-servico');
    final raw = r.data as List? ?? const [];
    return raw
        .cast<Map>()
        .map((m) => ClienteOsHistorico.fromJson(m.cast<String, dynamic>()))
        .toList();
  } on DioException {
    return const <ClienteOsHistorico>[];
  }
});
