import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'dto.dart';

class CardDiaRepository {
  CardDiaRepository(this._dio);
  final Dio _dio;

  Future<CardDiaDto?> get() async {
    final r = await _dio.get('/api/v1/cliente-app/card-dia');
    final data = r.data;
    if (data == null) return null;
    return CardDiaDto.fromJson(data as Map<String, dynamic>);
  }
}

final cardDiaRepositoryProvider = Provider<CardDiaRepository>(
  (ref) => CardDiaRepository(ref.watch(apiClientProvider)),
);

final cardDiaProvider = FutureProvider<CardDiaDto?>(
  (ref) => ref.watch(cardDiaRepositoryProvider).get(),
);
