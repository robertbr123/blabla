import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'dto.dart';

class ManutencoesRepository {
  ManutencoesRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app/manutencoes';

  Future<List<ManutencaoBreakingDto>> list() async {
    final r = await _dio.get(_base);
    final items = (r.data as Map)['items'] as List? ?? const [];
    return items
        .map((j) =>
            ManutencaoBreakingDto.fromJson(j as Map<String, dynamic>))
        .toList();
  }
}

final manutencoesRepositoryProvider = Provider<ManutencoesRepository>(
  (ref) => ManutencoesRepository(ref.watch(apiClientProvider)),
);

final manutencoesAtivasProvider =
    FutureProvider<List<ManutencaoBreakingDto>>(
  (ref) => ref.watch(manutencoesRepositoryProvider).list(),
);
