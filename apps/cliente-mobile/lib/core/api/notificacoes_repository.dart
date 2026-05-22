import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'dto.dart';

class NotificacoesRepository {
  NotificacoesRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app/notificacoes';

  Future<List<NotificacaoDto>> list({int limit = 50}) async {
    final r = await _dio.get(_base, queryParameters: {'limit': limit});
    final raw = r.data;
    if (raw is! List) return const [];
    return raw
        .map((j) => NotificacaoDto.fromJson(j as Map<String, dynamic>))
        .toList();
  }

  Future<int> unreadCount() async {
    try {
      final r = await _dio.get('$_base/unread-count');
      return (r.data['count'] as int?) ?? 0;
    } catch (_) {
      return 0;
    }
  }

  Future<void> marcarLida(String id) async {
    await _dio.post('$_base/$id/lida');
  }

  Future<void> marcarTodasLidas() async {
    await _dio.post('$_base/marcar-todas-lidas');
  }

  Future<NotifPrefsDto> getPrefs() async {
    final r = await _dio.get('$_base/preferencias');
    return NotifPrefsDto.fromJson(r.data as Map<String, dynamic>);
  }

  Future<NotifPrefsDto> setPrefs(NotifPrefsDto prefs) async {
    final r = await _dio.put(
      '$_base/preferencias',
      data: prefs.toJson(),
    );
    return NotifPrefsDto.fromJson(r.data as Map<String, dynamic>);
  }
}

final notificacoesRepositoryProvider = Provider<NotificacoesRepository>(
  (ref) => NotificacoesRepository(ref.watch(apiClientProvider)),
);

final notificacoesProvider = FutureProvider<List<NotificacaoDto>>(
  (ref) => ref.watch(notificacoesRepositoryProvider).list(),
);

final notificacoesUnreadCountProvider = FutureProvider<int>(
  (ref) => ref.watch(notificacoesRepositoryProvider).unreadCount(),
);

final notifPrefsProvider = FutureProvider<NotifPrefsDto>(
  (ref) => ref.watch(notificacoesRepositoryProvider).getPrefs(),
);
