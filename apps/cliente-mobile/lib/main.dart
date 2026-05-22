import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/branding/brand_theme.dart';
import 'core/theme/theme_mode_controller.dart';
import 'router.dart';

@pragma('vm:entry-point')
Future<void> _bgHandler(RemoteMessage message) async {
  // OS exibe a notif sozinho; sem render no isolate de background.
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await Firebase.initializeApp();
    FirebaseMessaging.onBackgroundMessage(_bgHandler);
  } catch (_) {
    // sem firebase_options.dart → segue sem push (dev local)
  }
  runApp(const ProviderScope(child: ClienteApp()));
}

class ClienteApp extends ConsumerWidget {
  const ClienteApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    final themeMode = ref.watch(themeModeProvider);
    return MaterialApp.router(
      title: 'Ondeline',
      debugShowCheckedModeBanner: false,
      theme: BrandTheme.light(),
      darkTheme: BrandTheme.dark(),
      themeMode: themeMode,
      routerConfig: router,
      builder: (context, child) {
        // Tap fora de TextField fecha o teclado em todo o app.
        return GestureDetector(
          behavior: HitTestBehavior.translucent,
          onTap: () {
            final f = FocusManager.instance.primaryFocus;
            if (f != null && f.hasFocus) f.unfocus();
          },
          child: child,
        );
      },
    );
  }
}
