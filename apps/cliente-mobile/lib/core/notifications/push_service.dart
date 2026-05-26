import 'dart:async';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../router.dart';
import '../api/api_client.dart';
import 'local_notifications.dart';

/// Servico de registro de push token FCM no backend.
/// Idempotente — backend ignora se token nao mudou.
///
/// Uso:
/// - `registerPushToken(ref)` apos o user logar (em MainShell.initState).
/// - `clearPushToken(ref)` antes do logout pra parar de receber push.
class PushService {
  PushService(this._dio);
  final Dio _dio;

  final _local = LocalNotifications();

  static const _setUrl = '/api/v1/cliente-app/me/push-token';

  /// Rota pra qual navegar ao tocar a notificacao. O backend manda em
  /// `data: {"route": "/faturas"}`; sem isso caimos na central de notificacoes.
  String _routeFrom(RemoteMessage? m) {
    final r = m?.data['route'];
    if (r is String && r.startsWith('/')) return r;
    return '/notificacoes';
  }

  void _navigate(String route) {
    final ctx = rootNavigatorKey.currentContext;
    if (ctx != null) {
      GoRouter.of(ctx).go(route);
    }
  }

  /// Configura os 3 cenarios de recebimento de push:
  /// - foreground (app aberto): FCM nao mostra sozinho → exibimos local.
  /// - background→tap: `onMessageOpenedApp`.
  /// - app fechado→tap (cold start): `getInitialMessage`.
  Future<void> _setupListeners() async {
    await _local.init((payload) {
      if (payload != null && payload.startsWith('/')) _navigate(payload);
    });

    FirebaseMessaging.onMessage.listen((m) {
      final n = m.notification;
      if (n == null) return;
      _local.show(
        title: n.title ?? 'Ondeline',
        body: n.body ?? '',
        payload: _routeFrom(m),
      );
    });

    FirebaseMessaging.onMessageOpenedApp.listen((m) {
      _navigate(_routeFrom(m));
    });

    final initial = await FirebaseMessaging.instance.getInitialMessage();
    if (initial != null) {
      _navigate(_routeFrom(initial));
    }
  }

  Future<bool> _requestPermission() async {
    try {
      final settings = await FirebaseMessaging.instance.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );
      return settings.authorizationStatus == AuthorizationStatus.authorized ||
          settings.authorizationStatus == AuthorizationStatus.provisional;
    } catch (e) {
      if (kDebugMode) print('PushService.permission error: $e');
      return false;
    }
  }

  Future<String?> _getToken() async {
    try {
      return await FirebaseMessaging.instance.getToken();
    } catch (e) {
      if (kDebugMode) print('PushService.getToken error: $e');
      return null;
    }
  }

  String _platform() {
    if (Platform.isAndroid) return 'android';
    if (Platform.isIOS) return 'ios';
    return 'other';
  }

  Future<void> _send(String token) async {
    try {
      await _dio.post(
        _setUrl,
        data: {'token': token, 'platform': _platform()},
      );
    } catch (e) {
      if (kDebugMode) print('PushService.send error: $e');
    }
  }

  /// Pede permissao, pega token e envia pro backend.
  /// Tambem registra listener pra `onTokenRefresh` enquanto o app vive.
  /// Idempotente — chamar de novo nao causa duplicacao.
  StreamSubscription<String>? _refreshSub;
  bool _started = false;

  Future<void> start() async {
    if (_started) return;
    final permitido = await _requestPermission();
    if (!permitido) return;
    await _setupListeners();
    final token = await _getToken();
    if (token != null && token.isNotEmpty) {
      await _send(token);
    }
    _refreshSub?.cancel();
    _refreshSub = FirebaseMessaging.instance.onTokenRefresh.listen(
      (newToken) => _send(newToken),
      onError: (e) {
        if (kDebugMode) print('PushService.onTokenRefresh error: $e');
      },
    );
    _started = true;
  }

  /// Limpa token no backend (chamado no logout).
  Future<void> clear() async {
    try {
      await _dio.delete(_setUrl);
    } catch (e) {
      if (kDebugMode) print('PushService.clear error: $e');
    }
    _refreshSub?.cancel();
    _refreshSub = null;
    _started = false;
    try {
      await FirebaseMessaging.instance.deleteToken();
    } catch (_) {
      // OK se ja foi deletado.
    }
  }
}

final pushServiceProvider = Provider<PushService>(
  (ref) => PushService(ref.watch(apiClientProvider)),
);
