import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/auth/auth_repository.dart';
import 'core/push/fcm_service.dart';
import 'core/sync/sync_service.dart';
import 'core/theme.dart';
import 'router.dart';

/// Background isolate — top-level por exigencia do firebase_messaging.
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // App nao tem render aqui; so logamos. Conteudo da notif eh exibido pelo
  // sistema operacional (campo `notification` no payload do FCM).
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Firebase opcional: se firebase_options.dart nao existe, ignora.
  try {
    await Firebase.initializeApp();
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
  } catch (_) {
    // sem firebase_options.dart → roda sem push (dev local)
  }
  runApp(const ProviderScope(child: TecnicoApp()));
}

class TecnicoApp extends ConsumerStatefulWidget {
  const TecnicoApp({super.key});

  @override
  ConsumerState<TecnicoApp> createState() => _TecnicoAppState();
}

class _TecnicoAppState extends ConsumerState<TecnicoApp> {
  bool _bootstrapped = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (_bootstrapped) return;
      _bootstrapped = true;
      // Inicia sync (precisa de token salvo — se nao tiver, faz nada util).
      await ref.read(syncServiceProvider).start();
      // FCM: so se usuario logado e Firebase inicializado.
      final hasToken = await ref.read(hasTokenProvider.future);
      if (hasToken && Firebase.apps.isNotEmpty) {
        await ref.read(fcmServiceProvider).init();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'Técnico Ondeline',
      theme: buildLightTheme(),
      darkTheme: buildDarkTheme(),
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}
