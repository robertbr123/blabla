import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../contrato/contrato_atual_provider.dart';
import 'api_client.dart';

class RedeWifiInfo {
  RedeWifiInfo({required this.ssid});
  factory RedeWifiInfo.fromJson(Map<String, dynamic> j) =>
      RedeWifiInfo(ssid: j['ssid'] as String);
  final String ssid;
}

class RedeStatusDto {
  RedeStatusDto({
    required this.encontrada,
    required this.online,
    this.modelo,
    required this.redes,
  });

  factory RedeStatusDto.fromJson(Map<String, dynamic> j) => RedeStatusDto(
        encontrada: j['encontrada'] as bool,
        online: (j['online'] as bool?) ?? false,
        modelo: j['modelo'] as String?,
        redes: ((j['redes'] as List?) ?? const [])
            .map((e) => RedeWifiInfo.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  final bool encontrada;
  final bool online;
  final String? modelo;
  final List<RedeWifiInfo> redes;

  String get nomeRede => redes.isNotEmpty ? redes.first.ssid : 'Sua rede WiFi';
}

class RedeAparelho {
  RedeAparelho({required this.nome, required this.ip});
  factory RedeAparelho.fromJson(Map<String, dynamic> j) => RedeAparelho(
        nome: (j['nome'] as String?) ?? '',
        ip: (j['ip'] as String?) ?? '',
      );
  final String nome;
  final String ip;

  /// Nome pra exibir, com fallback quando a ONU nao reporta o hostname.
  String get nomeExibicao => nome.trim().isNotEmpty ? nome : 'Dispositivo';
}

class RedeAparelhosDto {
  RedeAparelhosDto({
    required this.encontrada,
    required this.total,
    required this.aparelhos,
    required this.saude,
  });

  factory RedeAparelhosDto.fromJson(Map<String, dynamic> j) => RedeAparelhosDto(
        encontrada: (j['encontrada'] as bool?) ?? false,
        total: (j['total'] as int?) ?? 0,
        aparelhos: ((j['aparelhos'] as List?) ?? const [])
            .map((e) => RedeAparelho.fromJson(e as Map<String, dynamic>))
            .toList(),
        saude: (j['saude'] as String?) ?? 'indisponivel',
      );

  final bool encontrada;
  final int total;
  final List<RedeAparelho> aparelhos;
  final String saude; // excelente | boa | fraca | indisponivel
}

class TrocaResultDto {
  TrocaResultDto({
    required this.status,
    required this.reiniciando,
    required this.aviso,
  });

  factory TrocaResultDto.fromJson(Map<String, dynamic> j) => TrocaResultDto(
        status: j['status'] as String,
        reiniciando: (j['reiniciando'] as bool?) ?? false,
        aviso: (j['aviso'] as String?) ?? '',
      );

  final String status;
  final bool reiniciando;
  final String aviso;
}

/// Lancada quando o backend responde 429 (cooldown anti-flood).
class CooldownException implements Exception {
  CooldownException(this.minutosRestantes);
  final int minutosRestantes;
}

class RedeRepository {
  RedeRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app/rede';

  Future<RedeStatusDto> status({String? contratoId}) async {
    final r = await _dio.get(
      '$_base/status',
      queryParameters: contratoId != null ? {'contrato_id': contratoId} : null,
    );
    return RedeStatusDto.fromJson(r.data as Map<String, dynamic>);
  }

  Future<RedeAparelhosDto> aparelhos({String? contratoId}) async {
    final r = await _dio.get(
      '$_base/aparelhos',
      queryParameters: contratoId != null ? {'contrato_id': contratoId} : null,
    );
    return RedeAparelhosDto.fromJson(r.data as Map<String, dynamic>);
  }

  Future<TrocaResultDto> trocarSenha(String senha, {String? contratoId}) async {
    try {
      final r = await _dio.post('$_base/wifi/senha', data: {
        'senha': senha,
        if (contratoId != null) 'contrato_id': contratoId,
      });
      return TrocaResultDto.fromJson(r.data as Map<String, dynamic>);
    } on DioException catch (e) {
      if (e.response?.statusCode == 429) {
        throw CooldownException(_minutosFrom(e.response?.data));
      }
      rethrow;
    }
  }

  int _minutosFrom(Object? data) {
    if (data is Map && data['detail'] is Map) {
      final m = (data['detail'] as Map)['minutos_restantes'];
      if (m is int) return m;
    }
    return 5;
  }
}

final redeRepositoryProvider = Provider<RedeRepository>(
  (ref) => RedeRepository(ref.watch(apiClientProvider)),
);

/// Status da rede do contrato SELECIONADO (observa contratoAtualProvider).
final redeStatusProvider = FutureProvider<RedeStatusDto>((ref) {
  final contratoId = ref.watch(contratoAtualProvider);
  return ref.watch(redeRepositoryProvider).status(contratoId: contratoId);
});

/// Dispositivos + saude do contrato selecionado.
final redeAparelhosProvider = FutureProvider<RedeAparelhosDto>((ref) {
  final contratoId = ref.watch(contratoAtualProvider);
  return ref.watch(redeRepositoryProvider).aparelhos(contratoId: contratoId);
});
