import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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

  /// Nome amigavel da rede pro hero (primeiro SSID, ou fallback).
  String get nomeRede => redes.isNotEmpty ? redes.first.ssid : 'Sua rede WiFi';
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

  Future<RedeStatusDto> status() async {
    final r = await _dio.get('$_base/status');
    return RedeStatusDto.fromJson(r.data as Map<String, dynamic>);
  }

  Future<TrocaResultDto> trocarSenha(String senha) async {
    try {
      final r = await _dio.post('$_base/wifi/senha', data: {'senha': senha});
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

/// Status da rede do cliente. O backend resolve a ONU iterando TODOS os
/// contratos do CPF, entao nao precisa de contrato_id aqui (MVP).
final redeStatusProvider = FutureProvider<RedeStatusDto>(
  (ref) => ref.watch(redeRepositoryProvider).status(),
);
