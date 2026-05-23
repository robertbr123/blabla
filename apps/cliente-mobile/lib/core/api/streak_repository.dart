import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

class StreakDto {
  StreakDto({required this.atual, required this.totalPagas});
  factory StreakDto.fromJson(Map<String, dynamic> j) => StreakDto(
        atual: (j['atual'] as int?) ?? 0,
        totalPagas: (j['total_pagas'] as int?) ?? 0,
      );
  final int atual;
  final int totalPagas;
}

class StreakRepository {
  StreakRepository(this._dio);
  final Dio _dio;

  Future<StreakDto> get() async {
    final r = await _dio.get('/api/v1/cliente-app/streak');
    return StreakDto.fromJson(r.data as Map<String, dynamic>);
  }
}

final streakRepositoryProvider = Provider<StreakRepository>(
  (ref) => StreakRepository(ref.watch(apiClientProvider)),
);

final streakProvider = FutureProvider<StreakDto>(
  (ref) => ref.watch(streakRepositoryProvider).get(),
);
