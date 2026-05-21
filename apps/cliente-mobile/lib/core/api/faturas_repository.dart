import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'dto.dart';

class FaturasRepository {
  FaturasRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app';

  Future<List<FaturaDto>> list({String? status}) async {
    final r = await _dio.get(
      '$_base/faturas',
      queryParameters: status == null ? null : {'status': status},
    );
    return ((r.data as Map)['items'] as List? ?? const [])
        .map((j) => FaturaDto.fromJson(j as Map<String, dynamic>))
        .toList();
  }

  Future<String> getPix(String tituloId) async {
    final r = await _dio.get('$_base/faturas/$tituloId/pix');
    return (r.data as Map)['codigo'] as String;
  }

  Future<String> getBoletoUrl(String tituloId) async {
    final r = await _dio.get('$_base/faturas/$tituloId/boleto');
    return (r.data as Map)['url'] as String;
  }
}

final faturasRepositoryProvider = Provider<FaturasRepository>(
  (ref) => FaturasRepository(ref.watch(apiClientProvider)),
);

final faturasAbertasProvider = FutureProvider<List<FaturaDto>>(
  (ref) => ref.watch(faturasRepositoryProvider).list(status: 'abertas'),
);

final faturasPagasProvider = FutureProvider<List<FaturaDto>>(
  (ref) => ref.watch(faturasRepositoryProvider).list(status: 'pagas'),
);
