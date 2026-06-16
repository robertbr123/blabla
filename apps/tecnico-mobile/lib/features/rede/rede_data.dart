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

/// Status da rede por CPF. O CPF vai no body (POST), nunca na URL, pra nao
/// vazar em access log. O backend resolve CPF -> SGP -> pppoe -> ONU.
final redeStatusProvider =
    FutureProvider.autoDispose.family<StatusRede, String>((ref, cpf) async {
  final dio = ref.watch(apiClientProvider);
  final r = await dio.post('/api/v1/rede/status', data: {'cpf': cpf});
  return StatusRede.fromJson(r.data as Map<String, dynamic>);
});

/// Troca a senha. Retorna o aviso pra UI. Lanca em erro (tratado na tela).
Future<String> trocarSenhaWifi(
  Dio dio, {
  required String cpf,
  required String senha,
  String? serial,
}) async {
  final r = await dio.post(
    '/api/v1/rede/wifi/senha',
    data: {
      'cpf': cpf,
      'senha': senha,
      if (serial != null && serial.isNotEmpty) 'serial': serial,
    },
  );
  return (r.data['aviso'] ?? 'Senha enviada.') as String;
}

class Aparelho {
  Aparelho({
    required this.nome,
    required this.ip,
    required this.mac,
    required this.ativo,
    this.interface = '',
  });
  final String nome;
  final String ip;
  final String mac;
  final bool ativo;
  final String interface;

  factory Aparelho.fromJson(Map<String, dynamic> j) => Aparelho(
        nome: (j['nome'] ?? '') as String,
        ip: (j['ip'] ?? '') as String,
        mac: (j['mac'] ?? '') as String,
        ativo: (j['ativo'] ?? false) as bool,
        interface: (j['interface'] ?? '') as String,
      );
}

class SinalFibra {
  SinalFibra({
    this.rxPower,
    this.txPower,
    this.statusGpon,
    this.conexaoPppoe,
    this.ipExterno,
    this.uptimeS,
    this.ultimoErro,
    this.vlan,
  });
  final double? rxPower;
  final double? txPower;
  final String? statusGpon;
  final String? conexaoPppoe;
  final String? ipExterno;
  final int? uptimeS;
  final String? ultimoErro;
  final int? vlan;

  factory SinalFibra.fromJson(Map<String, dynamic> j) => SinalFibra(
        rxPower: (j['rx_power'] as num?)?.toDouble(),
        txPower: (j['tx_power'] as num?)?.toDouble(),
        statusGpon: j['status_gpon'] as String?,
        conexaoPppoe: j['conexao_pppoe'] as String?,
        ipExterno: j['ip_externo'] as String?,
        uptimeS: (j['uptime_s'] as num?)?.toInt(),
        ultimoErro: j['ultimo_erro'] as String?,
        vlan: (j['vlan'] as num?)?.toInt(),
      );
}

class Diagnostico {
  Diagnostico({
    required this.encontrada,
    this.lastInform,
    this.aparelhos = const [],
    this.sinal,
    this.motivo,
  });
  final bool encontrada;
  final DateTime? lastInform;
  final List<Aparelho> aparelhos;
  final SinalFibra? sinal;
  final String? motivo;

  factory Diagnostico.fromJson(Map<String, dynamic> j) => Diagnostico(
        encontrada: (j['encontrada'] ?? false) as bool,
        lastInform: j['last_inform'] != null
            ? DateTime.tryParse(j['last_inform'] as String)?.toLocal()
            : null,
        aparelhos: ((j['aparelhos'] ?? []) as List)
            .map((e) => Aparelho.fromJson(e as Map<String, dynamic>))
            .toList(),
        sinal: j['sinal'] != null
            ? SinalFibra.fromJson(j['sinal'] as Map<String, dynamic>)
            : null,
        motivo: j['motivo'] as String?,
      );
}

/// Diagnostico read-only (aparelhos + sinal da fibra). CPF no body (POST).
final redeDiagnosticoProvider =
    FutureProvider.autoDispose.family<Diagnostico, String>((ref, cpf) async {
  final dio = ref.watch(apiClientProvider);
  final r = await dio.post('/api/v1/rede/diagnostico', data: {'cpf': cpf});
  return Diagnostico.fromJson(r.data as Map<String, dynamic>);
});
