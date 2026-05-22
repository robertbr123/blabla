import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'dto.dart';

class FaturasRepository {
  FaturasRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app';

  Future<List<FaturaDto>> list({String? status, bool force = false}) async {
    final qs = <String, dynamic>{};
    if (status != null) qs['status'] = status;
    if (force) qs['force'] = 'true';
    final r = await _dio.get(
      '$_base/faturas',
      queryParameters: qs.isEmpty ? null : qs,
    );
    return ((r.data as Map)['items'] as List? ?? const [])
        .map((j) => FaturaDto.fromJson(j as Map<String, dynamic>))
        .toList();
  }

  /// Pull-to-refresh: invalida cache do backend e re-busca.
  Future<({List<FaturaDto> abertas, List<FaturaDto> pagas})> refreshAll() async {
    final abertas = await list(status: 'abertas', force: true);
    // Pagas sem force — cache de 1h ja serve, foi invalidado na chamada anterior.
    final pagas = await list(status: 'pagas');
    return (abertas: abertas, pagas: pagas);
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
