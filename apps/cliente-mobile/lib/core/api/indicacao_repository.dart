import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'dto.dart';

class IndicacaoRepository {
  IndicacaoRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app/indicacao';

  Future<IndicacaoMeuDto> getMeu() async {
    final r = await _dio.get('$_base/meu');
    return IndicacaoMeuDto.fromJson(r.data as Map<String, dynamic>);
  }

  Future<List<IndicacaoTimelineItemDto>> getTimeline() async {
    final r = await _dio.get('$_base/timeline');
    final list = ((r.data as Map)['items'] as List? ?? const [])
        .map((j) => IndicacaoTimelineItemDto.fromJson(j as Map<String, dynamic>))
        .toList();
    return list;
  }

  /// Registra que o usuario tocou "Compartilhar via WhatsApp" na tela.
  /// Best-effort — falha nao trava o share.
  Future<void> registrarShare() async {
    try {
      await _dio.post('$_base/share');
    } catch (_) {
      // Analytics nao pode quebrar UX.
    }
  }
}

final indicacaoRepositoryProvider = Provider<IndicacaoRepository>(
  (ref) => IndicacaoRepository(ref.watch(apiClientProvider)),
);

final indicacaoMeuProvider = FutureProvider<IndicacaoMeuDto>(
  (ref) => ref.watch(indicacaoRepositoryProvider).getMeu(),
);

final indicacaoTimelineProvider =
    FutureProvider<List<IndicacaoTimelineItemDto>>(
  (ref) => ref.watch(indicacaoRepositoryProvider).getTimeline(),
);
