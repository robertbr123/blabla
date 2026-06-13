import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;

import '../../core/api/api_client.dart';
import '../../core/sync/planos_cache.dart';

class SgpPlano {
  final int id;
  final String? grupo;
  final String descricao;
  final double preco;
  final int download; // Kbps
  final int upload;
  final bool isFallback;
  final String? velocidadeLabel;

  SgpPlano({
    required this.id,
    required this.grupo,
    required this.descricao,
    required this.preco,
    required this.download,
    required this.upload,
    this.isFallback = false,
    this.velocidadeLabel,
  });

  factory SgpPlano.fromJson(Map<String, dynamic> j) => SgpPlano(
        id: (j['id'] as num).toInt(),
        grupo: j['grupo'] as String?,
        descricao: (j['descricao'] ?? '') as String,
        preco: (j['preco'] as num?)?.toDouble() ?? 0,
        download: ((j['download'] as num?) ?? 0).toInt(),
        upload: ((j['upload'] as num?) ?? 0).toInt(),
      );

  factory SgpPlano.fromConfigJson(Map<String, dynamic> j) => SgpPlano(
        id: (j['index'] as num).toInt(),
        grupo: null,
        descricao: (j['nome'] ?? '') as String,
        preco: (j['preco'] as num?)?.toDouble() ?? 0,
        download: 0,
        upload: 0,
        isFallback: true,
        velocidadeLabel: (j['velocidade'] as String?)?.trim(),
      );

  /// "46 Mbps" / "150 Mbps" — converte Kbps pra Mbps arredondado.
  String velocidadeStr() {
    final fallback = velocidadeLabel;
    if (fallback != null && fallback.isNotEmpty) {
      return fallback;
    }
    return '${(download / 1024).round()} Mbps';
  }
}

final planosProvider = FutureProvider.autoDispose<List<SgpPlano>>((ref) async {
  final dio = ref.watch(apiClientProvider);
  try {
    final r = await dio.get('/api/v1/sgp/planos');
    unawaited(writePlanosCache(r.data)); // aquece p/ offline
    return _decodeSgpPlanos(r.data);
  } on DioException catch (e) {
    if (_shouldFallbackToConfiguredPlans(e)) {
      try {
        final fallback = await dio.get('/api/v1/planos');
        return _decodeConfiguredPlanos(fallback.data);
      } on DioException {
        final cached = await readPlanosCache();
        if (cached != null) return _decodeSgpPlanos(cached);
        rethrow;
      }
    }
    final cached = await readPlanosCache();
    if (cached != null) return _decodeSgpPlanos(cached);
    rethrow;
  }
});

class CreateClienteCampoMaterial {
  final String itemId;
  final int quantidade;
  final String? serial;
  CreateClienteCampoMaterial({
    required this.itemId,
    required this.quantidade,
    this.serial,
  });

  Map<String, dynamic> toJson() => {
        'item_id': itemId,
        'quantidade': quantidade,
        if (serial != null) 'serial': serial,
      };
}

class CreateClienteCampoIn {
  final String cpf;
  final String nome;
  final String dob;
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
  final String? serial;
  final String? contrato;
  final String? observation;
  final double? latitude;
  final double? longitude;
  final double? locationAccuracy;
  final List<CreateClienteCampoMaterial> materiais;

  CreateClienteCampoIn({
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
    required this.serial,
    required this.contrato,
    required this.observation,
    required this.latitude,
    required this.longitude,
    required this.locationAccuracy,
    required this.materiais,
  });

  Map<String, dynamic> toJson() => {
        'cpf': cpf,
        'nome': nome,
        'dob': dob,
        'telefone': telefone,
        if (email != null) 'email': email,
        if (cep != null) 'cep': cep,
        'address': address,
        'number': number,
        if (complement != null) 'complement': complement,
        if (neighborhood != null) 'neighborhood': neighborhood,
        'city': city,
        if (state != null) 'state': state,
        if (planId != null) 'plan_id': planId,
        'plan_nome': planNome,
        if (pppoeUser != null) 'pppoe_user': pppoeUser,
        if (pppoePass != null) 'pppoe_pass': pppoePass,
        'due_date': dueDate,
        if (serial != null) 'serial': serial,
        if (contrato != null) 'contrato': contrato,
        if (observation != null) 'observation': observation,
        if (latitude != null) 'latitude': latitude,
        if (longitude != null) 'longitude': longitude,
        if (locationAccuracy != null) 'location_accuracy': locationAccuracy,
        if (materiais.isNotEmpty)
          'materiais': materiais.map((m) => m.toJson()).toList(),
      };
}

class ClienteFormActions {
  final Dio _dio;
  ClienteFormActions(this._dio);

  /// Cria cliente + baixa materiais atomicamente. Retorna o id do novo cliente.
  Future<String> criar(CreateClienteCampoIn body) async {
    final r = await _dio.post(
      '/api/v1/clientes-campo',
      data: body.toJson(),
    );
    return (r.data as Map)['id'] as String;
  }

  /// Upload de foto. `tipo`: serial | instalacao | speedtest | outro.
  Future<void> uploadFoto({
    required String clienteId,
    required String filePath,
    required String tipo,
  }) async {
    final filename = imageUploadFilename(filePath);
    final form = FormData.fromMap({
      'file': await MultipartFile.fromFile(filePath, filename: filename),
      'tipo': tipo,
    });
    await _dio.post(
      '/api/v1/clientes-campo/$clienteId/fotos',
      data: form,
    );
  }

  Future<void> removerFoto({
    required String clienteId,
    required int idx,
  }) async {
    await _dio.delete('/api/v1/clientes-campo/$clienteId/fotos/$idx');
  }
}

final clienteFormActionsProvider = Provider<ClienteFormActions>(
  (ref) => ClienteFormActions(ref.watch(apiClientProvider)),
);

String extractDioMessage(
  DioException error, {
  String fallback = 'Não consegui concluir a ação agora.',
}) {
  final data = error.response?.data;
  if (data is Map) {
    final detail = data['detail']?.toString().trim();
    if (detail != null && detail.isNotEmpty) {
      return detail;
    }
  }
  final message = error.message?.trim();
  if (message != null && message.isNotEmpty) {
    return message;
  }
  return fallback;
}

String imageUploadFilename(String filePath) {
  final trimmed = filePath.trim();
  if (trimmed.isEmpty) return 'foto.jpg';
  final basename = p.basename(trimmed);
  return basename.isEmpty ? 'foto.jpg' : basename;
}

List<SgpPlano> _decodeSgpPlanos(Object? data) {
  final raw = (data as Map).cast<String, dynamic>();
  return (raw['planos'] as List? ?? const [])
      .cast<Map>()
      .map((m) => SgpPlano.fromJson(m.cast<String, dynamic>()))
      .toList();
}

List<SgpPlano> _decodeConfiguredPlanos(Object? data) {
  return (data as List? ?? const [])
      .whereType<Map>()
      .map((m) => SgpPlano.fromConfigJson(m.cast<String, dynamic>()))
      .toList();
}

bool _shouldFallbackToConfiguredPlans(DioException error) {
  final code = error.response?.statusCode;
  return code == 502 ||
      code == 503 ||
      error.type == DioExceptionType.connectionError ||
      error.type == DioExceptionType.connectionTimeout ||
      error.type == DioExceptionType.receiveTimeout;
}
