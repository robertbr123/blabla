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

/// Lookup do CEP via API publica do ViaCEP (gratuita, brasileira).
/// Retorna null se CEP invalido ou nao encontrado.
Future<ViaCepAddress?> buscarCep(String cep) async {
  final digits = onlyDigits(cep);
  if (digits.length != 8) return null;
  final dio = Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 5),
    receiveTimeout: const Duration(seconds: 5),
  ));
  try {
    final r = await dio.get('https://viacep.com.br/ws/$digits/json/');
    if (r.data is Map && (r.data as Map).containsKey('erro')) {
      return null;
    }
    return ViaCepAddress.fromJson((r.data as Map).cast<String, dynamic>());
  } catch (_) {
    return null;
  } finally {
    dio.close();
  }
}
