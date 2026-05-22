import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../contrato/contrato_atual_provider.dart';
import 'api_client.dart';
import 'dto.dart';

class MeRepository {
  MeRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app';

  Future<MeDto> getMe({String? contratoId, bool force = false}) async {
    final qs = <String, dynamic>{};
    if (contratoId != null) qs['contrato_id'] = contratoId;
    if (force) qs['force'] = 'true';
    final r = await _dio.get(
      '$_base/me',
      queryParameters: qs.isEmpty ? null : qs,
    );
    return MeDto.fromJson(r.data as Map<String, dynamic>);
  }

  /// Pull-to-refresh: força invalidar cache SGP no backend.
  /// Útil quando admin adicionou/removeu contrato e cache ainda mostra antigo.
  Future<MeDto> refresh({String? contratoId}) =>
      getMe(contratoId: contratoId, force: true);

  Future<PlanoDto> getPlano() async {
    final r = await _dio.get('$_base/plano');
    return PlanoDto.fromJson(r.data as Map<String, dynamic>);
  }

  Future<List<AvisoDto>> getAvisos() async {
    final r = await _dio.get('$_base/avisos');
    final items = ((r.data as Map)['items'] as List? ?? const [])
        .map((j) => AvisoDto.fromJson(j as Map<String, dynamic>))
        .toList();
    return items;
  }

  Future<MeDto> patchMe({String? telefone, String? email}) async {
    final body = <String, dynamic>{};
    if (telefone != null) body['telefone'] = telefone;
    if (email != null) body['email'] = email;
    final r = await _dio.patch('$_base/me', data: body);
    return MeDto.fromJson(r.data as Map<String, dynamic>);
  }

  Future<bool> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    try {
      await _dio.post('$_base/me/password', data: {
        'current_password': currentPassword,
        'new_password': newPassword,
      });
      return true;
    } on DioException {
      return false;
    }
  }

  Future<bool> deleteMe() async {
    try {
      await _dio.delete('$_base/me');
      return true;
    } on DioException {
      return false;
    }
  }
}

final meRepositoryProvider = Provider<MeRepository>(
  (ref) => MeRepository(ref.watch(apiClientProvider)),
);

final meProvider = FutureProvider<MeDto>(
  (ref) {
    final contratoId = ref.watch(contratoAtualProvider);
    return ref.watch(meRepositoryProvider).getMe(contratoId: contratoId);
  },
);

final planoProvider = FutureProvider<PlanoDto>(
  (ref) => ref.watch(meRepositoryProvider).getPlano(),
);

final avisosProvider = FutureProvider<List<AvisoDto>>(
  (ref) => ref.watch(meRepositoryProvider).getAvisos(),
);
