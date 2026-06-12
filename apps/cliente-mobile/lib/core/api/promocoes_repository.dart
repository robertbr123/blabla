import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'dto.dart';

class PromocoesRepository {
  PromocoesRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app/promocoes';

  Future<List<PromocaoDto>> list() async {
    final r = await _dio.get(_base);
    final raw = r.data;
    if (raw is List) {
      return raw
          .map((j) => PromocaoDto.fromJson(j as Map<String, dynamic>))
          .toList();
    }
    return const [];
  }

  /// Registra evento de view ou click. Fire-and-forget — falha não trava UI.
  Future<void> registrarEvento(String promoId, String tipo) async {
    try {
      await _dio.post(
        '$_base/$promoId/evento',
        data: {'tipo': tipo},
      );
    } catch (_) {
      // Best-effort. Analytics não pode quebrar a home.
    }
  }

  Future<PromocaoDetalheDto> detalhe(String id) async {
    final r = await _dio.get('$_base/$id');
    return PromocaoDetalheDto.fromJson(r.data as Map<String, dynamic>);
  }

  /// Registra interesse (lead). NÃO é fire-and-forget — lead é dado de
  /// negócio; erro sobe pro caller mostrar retry.
  Future<bool> registrarInteresse(String id, {String? contratoId}) async {
    final r = await _dio.post(
      '$_base/$id/interesse',
      data: {'contrato_id': contratoId},
    );
    final data = r.data as Map<String, dynamic>;
    return (data['ja_registrado'] as bool?) ?? false;
  }
}

final promocoesRepositoryProvider = Provider<PromocoesRepository>(
  (ref) => PromocoesRepository(ref.watch(apiClientProvider)),
);

final promocoesProvider = FutureProvider<List<PromocaoDto>>(
  (ref) => ref.watch(promocoesRepositoryProvider).list(),
);

final promocaoDetalheProvider =
    FutureProvider.autoDispose.family<PromocaoDetalheDto, String>(
  (ref, id) => ref.watch(promocoesRepositoryProvider).detalhe(id),
);
