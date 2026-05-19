import 'dart:io';

import 'package:dio/dio.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';

/// Trata permissoes FCM, registra token no backend, exibe notificacoes em
/// foreground via flutter_local_notifications.
///
/// Background isolate handler precisa ser top-level — definido em main.dart
/// como `_firebaseMessagingBackgroundHandler`.
class FcmService {
  final Dio _dio;
  final FlutterLocalNotificationsPlugin _local =
      FlutterLocalNotificationsPlugin();
  String? _lastToken;

  FcmService(this._dio);

  Future<void> init() async {
    // 1. Permissão (iOS pede explícito; Android 13+ tbm).
    final settings = await FirebaseMessaging.instance.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    if (settings.authorizationStatus == AuthorizationStatus.denied) {
      return;
    }

    // 2. Local notifications init (foreground display).
    const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosInit = DarwinInitializationSettings();
    await _local.initialize(
      const InitializationSettings(android: androidInit, iOS: iosInit),
    );

    // 3. Registra token + listener de rotação.
    final token = await FirebaseMessaging.instance.getToken();
    if (token != null) {
      await _registerToken(token);
    }
    FirebaseMessaging.instance.onTokenRefresh.listen(_registerToken);

    // 4. Mensagem em foreground → exibe notif local.
    FirebaseMessaging.onMessage.listen((msg) {
      final n = msg.notification;
      if (n == null) return;
      _local.show(
        msg.hashCode,
        n.title,
        n.body,
        const NotificationDetails(
          android: AndroidNotificationDetails(
            'ondeline_default',
            'Notificações Ondeline',
            importance: Importance.high,
            priority: Priority.high,
          ),
          iOS: DarwinNotificationDetails(),
        ),
      );
    });
  }

  Future<void> _registerToken(String token) async {
    if (token == _lastToken) return;
    _lastToken = token;
    try {
      await _dio.post(
        '/api/v1/tecnico/me/fcm-token',
        data: {
          'token': token,
          'platform': Platform.isIOS ? 'ios' : 'android',
        },
      );
    } catch (_) {
      // Best-effort — proximo ciclo tenta de novo.
    }
  }

  Future<void> revoke() async {
    final token = _lastToken;
    if (token == null) return;
    try {
      await _dio.post(
        '/api/v1/tecnico/me/fcm-token/revoke',
        data: {'token': token},
      );
    } catch (_) {}
    _lastToken = null;
  }
}

final fcmServiceProvider = Provider<FcmService>((ref) {
  return FcmService(ref.watch(apiClientProvider));
});
