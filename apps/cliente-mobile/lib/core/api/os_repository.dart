import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'dto.dart';

class OsRepository {
  OsRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app/os';

  Future<List<OsDto>> list() async {
    final r = await _dio.get(_base);
    return ((r.data as Map)['items'] as List? ?? const [])
        .map((j) => OsDto.fromJson(j as Map<String, dynamic>))
        .toList();
  }

  Future<OsDto> criar({
    required String tipo,
    required String descricao,
    Map<String, dynamic> payload = const {},
  }) async {
    final r = await _dio.post(_base, data: {
      'tipo': tipo,
      'descricao': descricao,
      'payload': payload,
    });
    return OsDto.fromJson(r.data as Map<String, dynamic>);
  }
}

final osRepositoryProvider = Provider<OsRepository>(
  (ref) => OsRepository(ref.watch(apiClientProvider)),
);

final osListProvider = FutureProvider<List<OsDto>>(
  (ref) => ref.watch(osRepositoryProvider).list(),
);
