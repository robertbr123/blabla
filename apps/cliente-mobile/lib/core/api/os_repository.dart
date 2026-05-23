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

  Future<void> submeterNps({
    required String osId,
    required int score,
    String? comentario,
    bool? tecnicoPontual,
    bool? tecnicoEducado,
    bool? tecnicoLimpou,
  }) async {
    await _dio.post('$_base/$osId/nps', data: {
      'score': score,
      if (comentario != null && comentario.isNotEmpty) 'comentario': comentario,
      if (tecnicoPontual != null) 'tecnico_pontual': tecnicoPontual,
      if (tecnicoEducado != null) 'tecnico_educado': tecnicoEducado,
      if (tecnicoLimpou != null) 'tecnico_limpou': tecnicoLimpou,
    });
  }
}

final osRepositoryProvider = Provider<OsRepository>(
  (ref) => OsRepository(ref.watch(apiClientProvider)),
);

final osListProvider = FutureProvider<List<OsDto>>(
  (ref) => ref.watch(osRepositoryProvider).list(),
);
