import 'package:dio/dio.dart';

import 'cpf_validator.dart' show onlyDigits;

class ViaCepAddress {
  final String cep;
  final String logradouro;
  final String bairro;
  final String localidade; // cidade
  final String uf;

  ViaCepAddress({
    required this.cep,
    required this.logradouro,
    required this.bairro,
    required this.localidade,
    required this.uf,
  });

  factory ViaCepAddress.fromJson(Map<String, dynamic> j) => ViaCepAddress(
        cep: (j['cep'] ?? '') as String,
        logradouro: (j['logradouro'] ?? '') as String,
        bairro: (j['bairro'] ?? '') as String,
        localidade: (j['localidade'] ?? '') as String,
        uf: (j['uf'] ?? '') as String,
      );
}

/// Resultado do lookup de CEP — distingue "não encontrado" de "erro de rede"
/// pra UI poder dar a mensagem certa (e não culpar o CEP quando é a conexão).
enum CepStatus { ok, notFound, networkError }

class CepResult {
  final CepStatus status;
  final ViaCepAddress? address;
  const CepResult(this.status, [this.address]);
}

/// Lookup do CEP via API publica do ViaCEP (gratuita, brasileira).
Future<CepResult> buscarCep(String cep) async {
  final digits = onlyDigits(cep);
  if (digits.length != 8) return const CepResult(CepStatus.notFound);
  final dio = Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 5),
    receiveTimeout: const Duration(seconds: 5),
  ));
  try {
    final r = await dio.get('https://viacep.com.br/ws/$digits/json/');
    if (r.data is Map && (r.data as Map).containsKey('erro')) {
      return const CepResult(CepStatus.notFound);
    }
    return CepResult(
      CepStatus.ok,
      ViaCepAddress.fromJson((r.data as Map).cast<String, dynamic>()),
    );
  } catch (_) {
    // Timeout/connection/parse — trata tudo como falha de rede (acionável).
    return const CepResult(CepStatus.networkError);
  } finally {
    dio.close();
  }
}
