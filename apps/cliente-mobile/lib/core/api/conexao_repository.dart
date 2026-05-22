import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../contrato/contrato_atual_provider.dart';
import 'api_client.dart';
import 'dto.dart';

class ConexaoRepository {
  ConexaoRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app/conexao';

  Future<ConexaoDto> get({String? contratoId}) async {
    final r = await _dio.get(
      _base,
      queryParameters: contratoId != null ? {'contrato_id': contratoId} : null,
    );
    return ConexaoDto.fromJson(r.data as Map<String, dynamic>);
  }
}

final conexaoRepositoryProvider = Provider<ConexaoRepository>(
  (ref) => ConexaoRepository(ref.watch(apiClientProvider)),
);

final conexaoProvider = FutureProvider<ConexaoDto>(
  (ref) {
    final contratoId = ref.watch(contratoAtualProvider);
    return ref.watch(conexaoRepositoryProvider).get(contratoId: contratoId);
  },
);
