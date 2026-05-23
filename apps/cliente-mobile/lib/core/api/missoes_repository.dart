import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

class MissaoItemDto {
  MissaoItemDto({
    required this.slug,
    required this.titulo,
    required this.descricao,
    required this.pontos,
    required this.periodicidade,
    required this.icon,
    required this.completadaHoje,
    required this.totalConcluida,
  });
  factory MissaoItemDto.fromJson(Map<String, dynamic> j) => MissaoItemDto(
        slug: j['slug'] as String,
        titulo: j['titulo'] as String,
        descricao: j['descricao'] as String,
        pontos: (j['pontos'] as int?) ?? 0,
        periodicidade: j['periodicidade'] as String,
        icon: (j['icon'] as String?) ?? 'star_rounded',
        completadaHoje: (j['completada_hoje'] as bool?) ?? false,
        totalConcluida: (j['total_concluida'] as int?) ?? 0,
      );
  final String slug;
  final String titulo;
  final String descricao;
  final int pontos;
  final String periodicidade; // 'diaria' | 'por_os' | 'on_the_fly'
  final String icon;
  final bool completadaHoje;
  final int totalConcluida;
}

class MissoesRepository {
  MissoesRepository(this._dio);
  final Dio _dio;

  Future<List<MissaoItemDto>> get() async {
    final r = await _dio.get('/api/v1/cliente-app/missoes');
    final items = ((r.data as Map)['items'] as List? ?? const [])
        .map((j) => MissaoItemDto.fromJson(j as Map<String, dynamic>))
        .toList();
    return items;
  }
}

final missoesRepositoryProvider = Provider<MissoesRepository>(
  (ref) => MissoesRepository(ref.watch(apiClientProvider)),
);

final missoesProvider = FutureProvider<List<MissaoItemDto>>(
  (ref) => ref.watch(missoesRepositoryProvider).get(),
);
