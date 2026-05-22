import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'dto.dart';

class IndicacaoRepository {
  IndicacaoRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app/indicacao';

  Future<IndicacaoMeuDto> getMeu() async {
    final r = await _dio.get('$_base/meu');
    return IndicacaoMeuDto.fromJson(r.data as Map<String, dynamic>);
  }
}

final indicacaoRepositoryProvider = Provider<IndicacaoRepository>(
  (ref) => IndicacaoRepository(ref.watch(apiClientProvider)),
);

final indicacaoMeuProvider = FutureProvider<IndicacaoMeuDto>(
  (ref) => ref.watch(indicacaoRepositoryProvider).getMeu(),
);
