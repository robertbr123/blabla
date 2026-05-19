import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';

class SgpPlano {
  final int id;
  final String? grupo;
  final String descricao;
  final double preco;
  final int download; // Kbps
  final int upload;

  SgpPlano({
    required this.id,
    required this.grupo,
    required this.descricao,
    required this.preco,
    required this.download,
    required this.upload,
  });

  factory SgpPlano.fromJson(Map<String, dynamic> j) => SgpPlano(
        id: (j['id'] as num).toInt(),
        grupo: j['grupo'] as String?,
        descricao: (j['descricao'] ?? '') as String,
        preco: (j['preco'] as num?)?.toDouble() ?? 0,
        download: ((j['download'] as num?) ?? 0).toInt(),
        upload: ((j['upload'] as num?) ?? 0).toInt(),
      );

  /// "46 Mbps" / "150 Mbps" — converte Kbps pra Mbps arredondado.
  String velocidadeStr() => '${(download / 1024).round()} Mbps';
}

final planosProvider = FutureProvider.autoDispose<List<SgpPlano>>((ref) async {
  final dio = ref.watch(apiClientProvider);
  final r = await dio.get('/api/v1/sgp/planos');
  final raw = (r.data as Map).cast<String, dynamic>();
  return (raw['planos'] as List? ?? const [])
      .cast<Map>()
      .map((m) => SgpPlano.fromJson(m.cast<String, dynamic>()))
      .toList();
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
}

final clienteFormActionsProvider = Provider<ClienteFormActions>(
  (ref) => ClienteFormActions(ref.watch(apiClientProvider)),
);
