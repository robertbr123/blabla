import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:intl/intl.dart';

import 'core/branding/brand_theme.dart';
import 'core/theme/theme_mode_controller.dart';
import 'firebase_options.dart';
import 'router.dart';

@pragma('vm:entry-point')
Future<void> _bgHandler(RemoteMessage message) async {
  // OS exibe a notif sozinho; sem render no isolate de background.
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // intl precisa carregar dados do locale antes de DateFormat/NumberFormat
  // com locale: 'pt_BR'. Sem isso → LocaleDataException nas telas Faturas
  // e Suporte (que formatam datas/valores).
  await initializeDateFormatting('pt_BR', null);
  Intl.defaultLocale = 'pt_BR';

  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
    FirebaseMessaging.onBackgroundMessage(_bgHandler);
  } catch (_) {
    // Init falhou (provavelmente sem internet/Google Play Services).
    // App segue sem push — telas funcionam normalmente.
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
      locale: const Locale('pt', 'BR'),
      supportedLocales: const [Locale('pt', 'BR')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
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
