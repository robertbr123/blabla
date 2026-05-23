import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'dto.dart';

class ContatosRepository {
  ContatosRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app/contatos';

  Future<List<ContatoOperadoraDto>> list() async {
    final r = await _dio.get(_base);
    final items = (r.data as Map)['items'] as List? ?? const [];
    return items
        .map((j) => ContatoOperadoraDto.fromJson(j as Map<String, dynamic>))
        .toList();
  }
}

final contatosRepositoryProvider = Provider<ContatosRepository>(
  (ref) => ContatosRepository(ref.watch(apiClientProvider)),
);

final contatosOperadoraProvider = FutureProvider<List<ContatoOperadoraDto>>(
  (ref) => ref.watch(contatosRepositoryProvider).list(),
);
