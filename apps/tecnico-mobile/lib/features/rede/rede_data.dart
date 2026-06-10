import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';

class RedeWlan {
  RedeWlan({required this.instancia, required this.ssid, required this.enabled});
  final int instancia;
  final String ssid;
  final bool enabled;

  factory RedeWlan.fromJson(Map<String, dynamic> j) => RedeWlan(
        instancia: j['instancia'] as int,
        ssid: (j['ssid'] ?? '') as String,
        enabled: (j['enabled'] ?? false) as bool,
      );
}

class StatusRede {
  StatusRede({
    required this.encontrada,
    this.modelo,
    this.fabricante,
    this.online = false,
    this.redes = const [],
    this.pppoeLogin,
    this.motivo,
  });
  final bool encontrada;
  final String? modelo;
  final String? fabricante;
  final bool online;
  final List<RedeWlan> redes;
  final String? pppoeLogin;
  final String? motivo;

  factory StatusRede.fromJson(Map<String, dynamic> j) => StatusRede(
        encontrada: (j['encontrada'] ?? false) as bool,
        modelo: j['modelo'] as String?,
        fabricante: j['fabricante'] as String?,
        online: (j['online'] ?? false) as bool,
        redes: ((j['redes'] ?? []) as List)
            .map((e) => RedeWlan.fromJson(e as Map<String, dynamic>))
            .toList(),
        pppoeLogin: j['pppoe_login'] as String?,
        motivo: j['motivo'] as String?,
      );
}

final redeStatusProvider =
    FutureProvider.autoDispose.family<StatusRede, String>((ref, clienteId) async {
  final dio = ref.watch(apiClientProvider);
  final r = await dio.get('/api/v1/rede/$clienteId');
  return StatusRede.fromJson(r.data as Map<String, dynamic>);
});

/// Troca a senha. Retorna o aviso pra UI. Lanca em erro (tratado na tela).
Future<String> trocarSenhaWifi(
  Dio dio, {
  required String clienteId,
  required String senha,
  String? serial,
}) async {
  final r = await dio.post(
    '/api/v1/rede/$clienteId/wifi/senha',
    data: {'senha': senha, if (serial != null && serial.isNotEmpty) 'serial': serial},
  );
  return (r.data['aviso'] ?? 'Senha enviada.') as String;
}
