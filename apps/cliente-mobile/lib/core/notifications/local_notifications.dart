import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Exibe notificacoes locais quando o app esta em FOREGROUND.
///
/// O FCM so mostra a notificacao automaticamente quando o app esta em
/// background ou fechado. Com o app aberto, `onMessage` dispara mas nada
/// aparece na barra — por isso recriamos a notificacao via este plugin.
///
/// O `channelId` aqui DEVE bater com o
/// `com.google.firebase.messaging.default_notification_channel_id` do
/// AndroidManifest, pra que background e foreground usem o mesmo canal.
class LocalNotifications {
  static const channelId = 'ondeline_default';
  static const _channelName = 'Notificacoes Ondeline';
  static const _channelDesc = 'Faturas, conexao e suporte';

  final _plugin = FlutterLocalNotificationsPlugin();
  bool _ready = false;

  /// `onTap` recebe o payload (rota) quando o user toca na notificacao local.
  Future<void> init(void Function(String? payload) onTap) async {
    if (_ready) return;
    try {
      const android = AndroidInitializationSettings('@drawable/ic_notification');
      const ios = DarwinInitializationSettings(
        // Permissao ja e pedida pelo firebase_messaging; nao repedir aqui.
        requestAlertPermission: false,
        requestBadgePermission: false,
        requestSoundPermission: false,
      );
      await _plugin.initialize(
        const InitializationSettings(android: android, iOS: ios),
        onDidReceiveNotificationResponse: (resp) => onTap(resp.payload),
      );

      // Cria o canal explicitamente (Android 8+). Sem isso a notif cai num
      // canal default sem nome amigavel.
      final androidImpl = _plugin.resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>();
      await androidImpl?.createNotificationChannel(
        const AndroidNotificationChannel(
          channelId,
          _channelName,
          description: _channelDesc,
          importance: Importance.high,
        ),
      );
      _ready = true;
    } catch (e) {
      if (kDebugMode) print('LocalNotifications.init error: $e');
    }
  }

  Future<void> show({
    required String title,
    required String body,
    String? payload,
  }) async {
    try {
      await _plugin.show(
        DateTime.now().millisecondsSinceEpoch ~/ 1000,
        title,
        body,
        const NotificationDetails(
          android: AndroidNotificationDetails(
            channelId,
            _channelName,
            channelDescription: _channelDesc,
            importance: Importance.high,
            priority: Priority.high,
            icon: '@drawable/ic_notification',
          ),
          iOS: DarwinNotificationDetails(),
        ),
        payload: payload,
      );
    } catch (e) {
      if (kDebugMode) print('LocalNotifications.show error: $e');
    }
  }
}
