import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'dto.dart';

class ConexaoRepository {
  ConexaoRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app/conexao';

  Future<ConexaoDto> get() async {
    final r = await _dio.get(_base);
    return ConexaoDto.fromJson(r.data as Map<String, dynamic>);
  }
}

final conexaoRepositoryProvider = Provider<ConexaoRepository>(
  (ref) => ConexaoRepository(ref.watch(apiClientProvider)),
);

final conexaoProvider = FutureProvider<ConexaoDto>(
  (ref) => ref.watch(conexaoRepositoryProvider).get(),
);
