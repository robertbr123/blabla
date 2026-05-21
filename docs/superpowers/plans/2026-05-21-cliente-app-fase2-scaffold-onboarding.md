# Cliente App — Fase 2: Scaffold Flutter + Onboarding

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`).

**Goal:** Criar o novo app Flutter `apps/cliente-mobile/` instalável, com identidade visual fintech-style, fluxo completo de onboarding (CPF → OTP → senha → biometria) e login funcionando contra o backend da Fase 1.

**Architecture:** Mirror enxuto do `apps/tecnico-mobile/` — mesmas libs (Riverpod, go_router, Dio, secure_storage, local_auth) mas SEM GPS, câmera, Drift e Firebase pesado. Tema próprio (paleta + tokens diferentes do técnico). Auth chama endpoints `/api/v1/cliente-app/auth/*` da Fase 1.

**Tech Stack:** Flutter 3.27+, Dart 3.6+, Riverpod, go_router, Dio, flutter_secure_storage, local_auth, google_fonts, firebase_core + firebase_messaging (opcional, igual técnico — graceful degradation).

**Spec:** `docs/superpowers/specs/2026-05-21-cliente-mobile-app-design.md`
**Plano anterior:** `docs/superpowers/plans/2026-05-21-cliente-app-fase1-auth-backend.md` (auth backend já no ar)

---

## File Structure

```
apps/cliente-mobile/
├── pubspec.yaml
├── analysis_options.yaml
├── android/                              ← gerado por flutter create
├── ios/                                  ← gerado por flutter create
├── lib/
│   ├── main.dart                          ← bootstrap + ProviderScope
│   ├── router.dart                        ← go_router com redirect baseado em auth
│   ├── core/
│   │   ├── api/
│   │   │   └── api_client.dart            ← Dio + interceptor bearer
│   │   ├── auth/
│   │   │   ├── auth_repository.dart       ← chama API Fase 1
│   │   │   ├── auth_state.dart            ← providers Riverpod
│   │   │   ├── auth_storage.dart          ← secure_storage wrapper
│   │   │   └── biometric_service.dart     ← local_auth wrapper
│   │   └── branding/
│   │       ├── brand_tokens.dart          ← cores, raios, espacos, sombras
│   │       └── brand_theme.dart           ← ThemeData light + dark
│   └── features/
│       ├── splash/splash_screen.dart
│       ├── onboarding/
│       │   ├── onboarding_cpf_screen.dart
│       │   ├── onboarding_otp_screen.dart
│       │   ├── onboarding_password_screen.dart
│       │   └── onboarding_biometric_screen.dart
│       ├── auth/login_screen.dart
│       └── home/home_placeholder_screen.dart
```

---

## Task 1: Scaffold do projeto Flutter

**Files:**
- Create directory: `apps/cliente-mobile/`
- Create: `apps/cliente-mobile/pubspec.yaml`
- Create: `apps/cliente-mobile/analysis_options.yaml`

- [ ] **Step 1: Rodar `flutter create`**

```bash
cd apps && flutter create --org dev.robertbr --project-name cliente_mobile --platforms=android,ios cliente-mobile
```
Expected: pasta `apps/cliente-mobile/` criada com android/, ios/, lib/main.dart default.

- [ ] **Step 2: Substituir o `pubspec.yaml`**

Sobrescrever `apps/cliente-mobile/pubspec.yaml`:

```yaml
name: cliente_mobile
description: App mobile do cliente final Ondeline — fatura, plano, OS e chat.
publish_to: 'none'
version: 0.1.0+1

environment:
  sdk: '>=3.6.0 <4.0.0'
  flutter: '>=3.27.0'

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.8

  # HTTP + auth
  dio: ^5.7.0
  flutter_secure_storage: ^9.2.2
  local_auth: ^2.3.0

  # State / nav
  flutter_riverpod: ^2.5.1
  go_router: ^14.6.1

  # Push (opcional — graceful se firebase_options.dart nao existir)
  firebase_core: ^3.6.0
  firebase_messaging: ^15.1.3

  # UI
  google_fonts: ^6.2.1

  # Utils
  intl: ^0.19.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^5.0.0

flutter:
  uses-material-design: true
```

- [ ] **Step 3: Substituir o `analysis_options.yaml`**

```yaml
include: package:flutter_lints/flutter.yaml

linter:
  rules:
    avoid_print: true
    prefer_const_constructors: true
    prefer_const_constructors_in_immutables: true
    prefer_const_declarations: true
    prefer_const_literals_to_create_immutables: true
    use_super_parameters: true
    sort_child_properties_last: true
```

- [ ] **Step 4: Pub get**

```bash
cd apps/cliente-mobile && flutter pub get
```
Expected: deps resolvidas sem erro.

- [ ] **Step 5: Commit**

```bash
git add apps/cliente-mobile/
git commit -m "feat(cliente-app): scaffold projeto Flutter cliente-mobile"
```

---

## Task 2: Design tokens + theme fintech

**Files:**
- Create: `apps/cliente-mobile/lib/core/branding/brand_tokens.dart`
- Create: `apps/cliente-mobile/lib/core/branding/brand_theme.dart`

**Direção visual:** **NÃO** copiar o vermelho/laranja Ondeline do técnico. Paleta nova fintech: roxo profundo + accent verde-menta (referência Nubank/Inter mas mais conservador). Cantos arredondados 24px, sombras suaves, sem gradientes berrantes.

- [ ] **Step 1: Criar `brand_tokens.dart`**

```dart
import 'package:flutter/material.dart';

/// Design tokens do app do cliente final. Paleta fintech-style.
class BrandTokens {
  BrandTokens._();

  // Cores principais
  static const Color primary = Color(0xFF3A2A6B); // Roxo profundo
  static const Color primaryDark = Color(0xFF241A47);
  static const Color accent = Color(0xFF1FB378); // Verde-menta
  static const Color accentDark = Color(0xFF158B5A);

  // Neutros (light)
  static const Color background = Color(0xFFF7F6FB);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color textPrimary = Color(0xFF1A1430);
  static const Color textSecondary = Color(0xFF6B6480);
  static const Color divider = Color(0xFFEDEAF3);

  // Neutros (dark)
  static const Color backgroundDark = Color(0xFF0F0B1F);
  static const Color surfaceDark = Color(0xFF1A1530);
  static const Color textPrimaryDark = Color(0xFFF5F2FF);
  static const Color textSecondaryDark = Color(0xFF9C95B8);

  // Status
  static const Color success = Color(0xFF1FB378);
  static const Color warning = Color(0xFFE8A33D);
  static const Color danger = Color(0xFFE0455A);
  static const Color info = Color(0xFF3B82F6);

  // Raios
  static const double radiusSm = 12;
  static const double radiusMd = 16;
  static const double radiusLg = 24;
  static const double radiusXl = 32;

  // Espacos
  static const double spaceXs = 4;
  static const double spaceSm = 8;
  static const double spaceMd = 16;
  static const double spaceLg = 24;
  static const double spaceXl = 32;
  static const double spaceXxl = 48;

  // Sombras
  static List<BoxShadow> shadowSoft = [
    BoxShadow(
      color: primary.withOpacity(0.06),
      blurRadius: 24,
      offset: const Offset(0, 8),
    ),
  ];

  static List<BoxShadow> shadowCard = [
    BoxShadow(
      color: primary.withOpacity(0.04),
      blurRadius: 16,
      offset: const Offset(0, 4),
    ),
  ];
}
```

- [ ] **Step 2: Criar `brand_theme.dart`**

```dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'brand_tokens.dart';

class BrandTheme {
  BrandTheme._();

  static ThemeData light() {
    final base = ColorScheme.fromSeed(
      seedColor: BrandTokens.primary,
      brightness: Brightness.light,
      primary: BrandTokens.primary,
      secondary: BrandTokens.accent,
      surface: BrandTokens.surface,
      error: BrandTokens.danger,
    );
    return _build(base, BrandTokens.background, BrandTokens.textPrimary,
        BrandTokens.textSecondary, BrandTokens.divider);
  }

  static ThemeData dark() {
    final base = ColorScheme.fromSeed(
      seedColor: BrandTokens.primary,
      brightness: Brightness.dark,
      primary: BrandTokens.primary,
      secondary: BrandTokens.accent,
      surface: BrandTokens.surfaceDark,
      error: BrandTokens.danger,
    );
    return _build(base, BrandTokens.backgroundDark, BrandTokens.textPrimaryDark,
        BrandTokens.textSecondaryDark, Colors.white12);
  }

  static ThemeData _build(
    ColorScheme scheme,
    Color background,
    Color textPrimary,
    Color textSecondary,
    Color divider,
  ) {
    final textTheme = GoogleFonts.interTextTheme().apply(
      bodyColor: textPrimary,
      displayColor: textPrimary,
    );

    return ThemeData(
      colorScheme: scheme,
      scaffoldBackgroundColor: background,
      textTheme: textTheme,
      useMaterial3: true,
      appBarTheme: AppBarTheme(
        backgroundColor: background,
        foregroundColor: textPrimary,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: textTheme.titleLarge?.copyWith(
          fontWeight: FontWeight.w700,
          color: textPrimary,
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(56),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          ),
          textStyle: textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size.fromHeight(56),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: scheme.surface,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: BrandTokens.spaceMd,
          vertical: BrandTokens.spaceMd,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          borderSide: BorderSide(color: divider),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          borderSide: BorderSide(color: divider),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          borderSide: BorderSide(color: scheme.primary, width: 2),
        ),
      ),
      dividerTheme: DividerThemeData(color: divider, thickness: 1),
      cardTheme: CardTheme(
        elevation: 0,
        color: scheme.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        ),
        margin: EdgeInsets.zero,
      ),
    );
  }
}
```

- [ ] **Step 3: Pub get pra puxar google_fonts**

```bash
cd apps/cliente-mobile && flutter pub get && flutter analyze lib/core/branding
```
Expected: 0 issues.

- [ ] **Step 4: Commit**

```bash
git add apps/cliente-mobile/lib/core/branding/
git commit -m "feat(cliente-app): design tokens + theme fintech-style"
```

---

## Task 3: API client + Auth storage

**Files:**
- Create: `apps/cliente-mobile/lib/core/api/api_client.dart`
- Create: `apps/cliente-mobile/lib/core/auth/auth_storage.dart`

- [ ] **Step 1: Criar `auth_storage.dart`**

```dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _kAccess = 'cliente_access_token';
const _kCpfLast4 = 'cliente_cpf_last4';
const _kNome = 'cliente_nome';
const _kBiometric = 'cliente_biometric_enabled';

final _storage = const FlutterSecureStorage(
  aOptions: AndroidOptions(encryptedSharedPreferences: true),
);

Future<String?> readAccessToken() => _storage.read(key: _kAccess);
Future<void> writeAccessToken(String token) =>
    _storage.write(key: _kAccess, value: token);

Future<void> writeSession({
  required String cpfLast4,
  required String nome,
  required bool biometricEnabled,
}) async {
  await _storage.write(key: _kCpfLast4, value: cpfLast4);
  await _storage.write(key: _kNome, value: nome);
  await _storage.write(key: _kBiometric, value: biometricEnabled.toString());
}

Future<String?> readCpfLast4() => _storage.read(key: _kCpfLast4);
Future<String?> readNome() => _storage.read(key: _kNome);
Future<bool> readBiometricEnabled() async {
  final v = await _storage.read(key: _kBiometric);
  return v == 'true';
}

Future<void> writeBiometricEnabled(bool enabled) =>
    _storage.write(key: _kBiometric, value: enabled.toString());

Future<void> clearAuth() async {
  await _storage.delete(key: _kAccess);
  await _storage.delete(key: _kCpfLast4);
  await _storage.delete(key: _kNome);
  await _storage.delete(key: _kBiometric);
}
```

- [ ] **Step 2: Criar `api_client.dart`**

```dart
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_storage.dart';

const apiBaseUrl = String.fromEnvironment(
  'API_URL',
  defaultValue: 'https://apiblabla.robertbr.dev',
);

final apiClientProvider = Provider<Dio>((ref) {
  final dio = Dio(BaseOptions(
    baseUrl: apiBaseUrl,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 30),
    headers: {'Accept': 'application/json'},
  ));

  dio.interceptors.add(InterceptorsWrapper(
    onRequest: (options, handler) async {
      final skipAuth = options.extra['skipAuth'] == true;
      if (!skipAuth) {
        final token = await readAccessToken();
        if (token != null && token.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $token';
        }
      }
      handler.next(options);
    },
    onError: (e, handler) async {
      final code = e.response?.statusCode;
      final isAuthFlow = e.requestOptions.path.startsWith('/api/v1/cliente-app/auth/');
      if (code == 401 && !isAuthFlow) {
        await clearAuth();
      }
      handler.next(e);
    },
  ));

  return dio;
});
```

- [ ] **Step 3: Analyze**

```bash
cd apps/cliente-mobile && flutter analyze lib/core/api lib/core/auth
```
Expected: 0 issues.

- [ ] **Step 4: Commit**

```bash
git add apps/cliente-mobile/lib/core/api/ apps/cliente-mobile/lib/core/auth/auth_storage.dart
git commit -m "feat(cliente-app): API client + secure storage"
```

---

## Task 4: Auth repository

**Files:**
- Create: `apps/cliente-mobile/lib/core/auth/auth_repository.dart`

- [ ] **Step 1: Implementar**

```dart
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import 'auth_storage.dart';

class AuthRepository {
  AuthRepository(this._dio);
  final Dio _dio;

  static const _base = '/api/v1/cliente-app/auth';

  Future<RegisterStartResult> registerStart(String cpf) async {
    try {
      final r = await _dio.post(
        '$_base/register/start',
        data: {'cpf': cpf},
        options: Options(extra: {'skipAuth': true}),
      );
      return RegisterStartResult.ok(maskedPhone: r.data['masked_phone'] as String);
    } on DioException catch (e) {
      return RegisterStartResult.error(_messageFromDio(e));
    }
  }

  Future<RegisterVerifyResult> registerVerify(String cpf, String code) async {
    try {
      final r = await _dio.post(
        '$_base/register/verify',
        data: {'cpf': cpf, 'code': code},
        options: Options(extra: {'skipAuth': true}),
      );
      return RegisterVerifyResult.ok(setupToken: r.data['setup_token'] as String);
    } on DioException catch (e) {
      return RegisterVerifyResult.error(_messageFromDio(e));
    }
  }

  Future<AuthResult> registerPassword({
    required String setupToken,
    required String password,
    required String cpfLast4,
    required String nome,
  }) async {
    try {
      final r = await _dio.post(
        '$_base/register/password',
        data: {'setup_token': setupToken, 'password': password},
        options: Options(extra: {'skipAuth': true}),
      );
      final token = r.data['access_token'] as String;
      await writeAccessToken(token);
      await writeSession(cpfLast4: cpfLast4, nome: nome, biometricEnabled: false);
      return AuthResult.ok(accessToken: token);
    } on DioException catch (e) {
      return AuthResult.error(_messageFromDio(e));
    }
  }

  Future<AuthResult> login({
    required String cpf,
    required String password,
  }) async {
    try {
      final r = await _dio.post(
        '$_base/login',
        data: {'cpf': cpf, 'password': password},
        options: Options(extra: {'skipAuth': true}),
      );
      final token = r.data['access_token'] as String;
      await writeAccessToken(token);
      // Nome real vem do /me na Fase 3; por ora preserva o que houver salvo.
      final existingNome = (await readNome()) ?? '';
      final cpfDigits = cpf.replaceAll(RegExp(r'\D'), '');
      await writeSession(
        cpfLast4: cpfDigits.substring(cpfDigits.length - 4),
        nome: existingNome,
        biometricEnabled: await readBiometricEnabled(),
      );
      return AuthResult.ok(accessToken: token);
    } on DioException catch (e) {
      return AuthResult.error(_messageFromDio(e));
    }
  }

  Future<bool> forgot(String cpf) async {
    try {
      await _dio.post(
        '$_base/forgot',
        data: {'cpf': cpf},
        options: Options(extra: {'skipAuth': true}),
      );
      return true;
    } on DioException {
      return false;
    }
  }

  Future<void> logout() => clearAuth();

  String _messageFromDio(DioException e) {
    final d = e.response?.data;
    if (d is Map && d['detail'] is String) return d['detail'] as String;
    final code = e.response?.statusCode;
    if (code == 404) return 'CPF nao encontrado';
    if (code == 409) return 'Ja existe cadastro pra esse CPF';
    if (code == 401) return 'Credenciais invalidas';
    if (code == 429) return 'Muitas tentativas. Tente novamente em alguns minutos';
    return 'Falha de conexao. Tente novamente.';
  }
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(ref.watch(apiClientProvider));
});

sealed class RegisterStartResult {
  const RegisterStartResult();
  factory RegisterStartResult.ok({required String maskedPhone}) =
      RegisterStartOk;
  factory RegisterStartResult.error(String message) = RegisterStartError;
}

class RegisterStartOk extends RegisterStartResult {
  const RegisterStartOk({required this.maskedPhone});
  final String maskedPhone;
}

class RegisterStartError extends RegisterStartResult {
  const RegisterStartError(this.message);
  final String message;
}

sealed class RegisterVerifyResult {
  const RegisterVerifyResult();
  factory RegisterVerifyResult.ok({required String setupToken}) =
      RegisterVerifyOk;
  factory RegisterVerifyResult.error(String message) = RegisterVerifyError;
}

class RegisterVerifyOk extends RegisterVerifyResult {
  const RegisterVerifyOk({required this.setupToken});
  final String setupToken;
}

class RegisterVerifyError extends RegisterVerifyResult {
  const RegisterVerifyError(this.message);
  final String message;
}

sealed class AuthResult {
  const AuthResult();
  factory AuthResult.ok({required String accessToken}) = AuthOk;
  factory AuthResult.error(String message) = AuthError;
}

class AuthOk extends AuthResult {
  const AuthOk({required this.accessToken});
  final String accessToken;
}

class AuthError extends AuthResult {
  const AuthError(this.message);
  final String message;
}
```

- [ ] **Step 2: Analyze**

```bash
cd apps/cliente-mobile && flutter analyze lib/core/auth/auth_repository.dart
```
Expected: 0 issues.

- [ ] **Step 3: Commit**

```bash
git add apps/cliente-mobile/lib/core/auth/auth_repository.dart
git commit -m "feat(cliente-app): auth repository com fluxo register/login/forgot"
```

---

## Task 5: Biometric service + auth state providers

**Files:**
- Create: `apps/cliente-mobile/lib/core/auth/biometric_service.dart`
- Create: `apps/cliente-mobile/lib/core/auth/auth_state.dart`

- [ ] **Step 1: `biometric_service.dart`**

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:local_auth/local_auth.dart';

class BiometricService {
  BiometricService(this._auth);
  final LocalAuthentication _auth;

  Future<bool> isAvailable() async {
    try {
      final supported = await _auth.isDeviceSupported();
      final canCheck = await _auth.canCheckBiometrics;
      return supported && canCheck;
    } catch (_) {
      return false;
    }
  }

  Future<bool> authenticate(String reason) async {
    try {
      return await _auth.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(
          biometricOnly: false,
          stickyAuth: true,
        ),
      );
    } catch (_) {
      return false;
    }
  }
}

final biometricServiceProvider = Provider<BiometricService>(
  (ref) => BiometricService(LocalAuthentication()),
);
```

- [ ] **Step 2: `auth_state.dart`**

```dart
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_storage.dart';

/// Notifier simples — bate em secure_storage para descobrir se ha sessao.
class AuthRefresh extends ChangeNotifier {
  void bump() => notifyListeners();
}

final authRefreshProvider = ChangeNotifierProvider<AuthRefresh>(
  (ref) => AuthRefresh(),
);

final hasTokenProvider = FutureProvider<bool>((ref) async {
  ref.watch(authRefreshProvider);
  final t = await readAccessToken();
  return t != null && t.isNotEmpty;
});

class SessionSnapshot {
  const SessionSnapshot({
    required this.cpfLast4,
    required this.nome,
    required this.biometricEnabled,
  });
  final String cpfLast4;
  final String nome;
  final bool biometricEnabled;
}

final sessionSnapshotProvider = FutureProvider<SessionSnapshot?>((ref) async {
  ref.watch(authRefreshProvider);
  final cpfLast4 = await readCpfLast4();
  if (cpfLast4 == null) return null;
  return SessionSnapshot(
    cpfLast4: cpfLast4,
    nome: (await readNome()) ?? '',
    biometricEnabled: await readBiometricEnabled(),
  );
});
```

- [ ] **Step 3: Analyze**

```bash
cd apps/cliente-mobile && flutter analyze lib/core/auth
```
Expected: 0 issues.

- [ ] **Step 4: Commit**

```bash
git add apps/cliente-mobile/lib/core/auth/biometric_service.dart apps/cliente-mobile/lib/core/auth/auth_state.dart
git commit -m "feat(cliente-app): biometric service + auth providers"
```

---

## Task 6: Splash + Home placeholder + main + router

**Files:**
- Create: `apps/cliente-mobile/lib/features/splash/splash_screen.dart`
- Create: `apps/cliente-mobile/lib/features/home/home_placeholder_screen.dart`
- Overwrite: `apps/cliente-mobile/lib/main.dart`
- Create: `apps/cliente-mobile/lib/router.dart`

- [ ] **Step 1: `splash_screen.dart`**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';

class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _decide());
  }

  Future<void> _decide() async {
    await Future.delayed(const Duration(milliseconds: 600));
    if (!mounted) return;
    final hasToken = await ref.read(hasTokenProvider.future).catchError((_) => false);
    if (!mounted) return;
    context.go(hasToken ? '/home' : '/onboarding/cpf');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: BrandTokens.primary,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 84,
              height: 84,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
              ),
              alignment: Alignment.center,
              child: Text(
                'O',
                style: TextStyle(
                  fontSize: 48,
                  fontWeight: FontWeight.w900,
                  color: BrandTokens.primary,
                ),
              ),
            ),
            const SizedBox(height: BrandTokens.spaceLg),
            const Text(
              'Ondeline',
              style: TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: `home_placeholder_screen.dart`**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';

class HomePlaceholderScreen extends ConsumerWidget {
  const HomePlaceholderScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionSnapshotProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Inicio'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await ref.read(authRepositoryProvider).logout();
              ref.read(authRefreshProvider).bump();
              if (context.mounted) context.go('/onboarding/cpf');
            },
          ),
        ],
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceXl),
          child: session.when(
            data: (s) => Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.check_circle_outline,
                    color: BrandTokens.success, size: 72),
                const SizedBox(height: BrandTokens.spaceMd),
                Text(
                  'Voce esta dentro!',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: BrandTokens.spaceSm),
                Text(
                  s == null
                      ? 'Sem sessao'
                      : 'CPF ***.***.***-${s.cpfLast4}',
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: BrandTokens.spaceLg),
                Text(
                  'Suas faturas, plano e suporte chegam aqui nas proximas fases.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: BrandTokens.textSecondary,
                      ),
                ),
              ],
            ),
            loading: () => const CircularProgressIndicator(),
            error: (_, __) => const Text('Erro carregando sessao'),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 3: `router.dart`**

```dart
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/auth/auth_state.dart';
import 'features/auth/login_screen.dart';
import 'features/home/home_placeholder_screen.dart';
import 'features/onboarding/onboarding_biometric_screen.dart';
import 'features/onboarding/onboarding_cpf_screen.dart';
import 'features/onboarding/onboarding_otp_screen.dart';
import 'features/onboarding/onboarding_password_screen.dart';
import 'features/splash/splash_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: ref.watch(authRefreshProvider),
    redirect: (context, state) async {
      final loc = state.matchedLocation;
      if (loc == '/splash') return null;

      bool has = false;
      try {
        has = await ref
            .read(hasTokenProvider.future)
            .timeout(const Duration(seconds: 3), onTimeout: () => false);
      } catch (_) {}

      final inAuthArea = loc.startsWith('/onboarding') || loc == '/login';
      if (!has && !inAuthArea) return '/onboarding/cpf';
      if (has && inAuthArea) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, __) => const SplashScreen()),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(
        path: '/onboarding/cpf',
        builder: (_, __) => const OnboardingCpfScreen(),
      ),
      GoRoute(
        path: '/onboarding/otp',
        builder: (_, state) {
          final extra = state.extra as Map<String, String>?;
          return OnboardingOtpScreen(
            cpf: extra?['cpf'] ?? '',
            maskedPhone: extra?['masked_phone'] ?? '',
          );
        },
      ),
      GoRoute(
        path: '/onboarding/password',
        builder: (_, state) {
          final extra = state.extra as Map<String, String>?;
          return OnboardingPasswordScreen(
            setupToken: extra?['setup_token'] ?? '',
            cpf: extra?['cpf'] ?? '',
          );
        },
      ),
      GoRoute(
        path: '/onboarding/biometric',
        builder: (_, __) => const OnboardingBiometricScreen(),
      ),
      GoRoute(path: '/home', builder: (_, __) => const HomePlaceholderScreen()),
    ],
  );
});
```

- [ ] **Step 4: `main.dart`**

```dart
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/branding/brand_theme.dart';
import 'router.dart';

@pragma('vm:entry-point')
Future<void> _bgHandler(RemoteMessage message) async {
  // sem render no isolate de background — OS exibe a notif sozinho.
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await Firebase.initializeApp();
    FirebaseMessaging.onBackgroundMessage(_bgHandler);
  } catch (_) {
    // sem firebase_options.dart → segue sem push
  }
  runApp(const ProviderScope(child: ClienteApp()));
}

class ClienteApp extends ConsumerWidget {
  const ClienteApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'Ondeline',
      debugShowCheckedModeBanner: false,
      theme: BrandTheme.light(),
      darkTheme: BrandTheme.dark(),
      themeMode: ThemeMode.system,
      routerConfig: router,
    );
  }
}
```

- [ ] **Step 5: Analyze**

```bash
cd apps/cliente-mobile && flutter analyze lib/main.dart lib/router.dart lib/features/splash lib/features/home
```
Expected: 0 issues (assumindo que onboarding/login screens da Task 7/8 ainda não existem, o analyze vai falhar no import — rode esse step DEPOIS de Task 8 ou crie stubs vazios das 5 telas primeiro).

**IMPORTANT:** Crie stubs vazios das telas referenciadas no router antes do analyze:
- `apps/cliente-mobile/lib/features/auth/login_screen.dart` → `class LoginScreen extends StatelessWidget { const LoginScreen({super.key}); @override Widget build(_) => const Scaffold(); }`
- Idem `onboarding_cpf_screen.dart`, `onboarding_otp_screen.dart`, `onboarding_password_screen.dart`, `onboarding_biometric_screen.dart` com a assinatura usada no router (incluindo construtor pra OTP e Password).

- [ ] **Step 6: Commit**

```bash
git add apps/cliente-mobile/lib/
git commit -m "feat(cliente-app): splash + home placeholder + main + router"
```

---

## Task 7: Onboarding — telas (CPF, OTP, senha, biometria)

**Files:**
- Replace stubs with real screens:
  - `apps/cliente-mobile/lib/features/onboarding/onboarding_cpf_screen.dart`
  - `apps/cliente-mobile/lib/features/onboarding/onboarding_otp_screen.dart`
  - `apps/cliente-mobile/lib/features/onboarding/onboarding_password_screen.dart`
  - `apps/cliente-mobile/lib/features/onboarding/onboarding_biometric_screen.dart`

**Design comum:** AppBar transparente sem título, headline H1 + subtítulo + input + CTA fixo no bottom. Erros em SnackBar. Sem teclado de número exigir formatar (deixe simples; mask vem depois).

- [ ] **Step 1: `onboarding_cpf_screen.dart`**

```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/branding/brand_tokens.dart';

class OnboardingCpfScreen extends ConsumerStatefulWidget {
  const OnboardingCpfScreen({super.key});

  @override
  ConsumerState<OnboardingCpfScreen> createState() => _OnboardingCpfScreenState();
}

class _OnboardingCpfScreenState extends ConsumerState<OnboardingCpfScreen> {
  final _ctrl = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _continue() async {
    final cpf = _ctrl.text.replaceAll(RegExp(r'\D'), '');
    if (cpf.length != 11) {
      _toast('Informe um CPF valido com 11 digitos');
      return;
    }
    setState(() => _loading = true);
    final r = await ref.read(authRepositoryProvider).registerStart(cpf);
    setState(() => _loading = false);
    if (!mounted) return;
    switch (r) {
      case RegisterStartOk(:final maskedPhone):
        context.push('/onboarding/otp', extra: {
          'cpf': cpf,
          'masked_phone': maskedPhone,
        });
      case RegisterStartError(:final message):
        if (message.toLowerCase().contains('ja cadastrado')) {
          // CPF ja tem conta — vai pro login
          context.go('/login', extra: {'cpf': cpf});
        } else {
          _toast(message);
        }
    }
  }

  void _toast(String s) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Vamos te encontrar',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Text(
                'Digite seu CPF pra continuar.',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: BrandTokens.textSecondary,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceXl),
              TextField(
                controller: _ctrl,
                keyboardType: TextInputType.number,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(11),
                ],
                decoration: const InputDecoration(labelText: 'CPF'),
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const Spacer(),
              FilledButton(
                onPressed: _loading ? null : _continue,
                child: _loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Continuar'),
              ),
              TextButton(
                onPressed: () => context.go('/login'),
                child: const Text('Ja tenho conta'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: `onboarding_otp_screen.dart`**

```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/branding/brand_tokens.dart';

class OnboardingOtpScreen extends ConsumerStatefulWidget {
  const OnboardingOtpScreen({super.key, required this.cpf, required this.maskedPhone});
  final String cpf;
  final String maskedPhone;

  @override
  ConsumerState<OnboardingOtpScreen> createState() => _OnboardingOtpScreenState();
}

class _OnboardingOtpScreenState extends ConsumerState<OnboardingOtpScreen> {
  final _ctrl = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _continue() async {
    final code = _ctrl.text.trim();
    if (code.length != 6) {
      _toast('Codigo deve ter 6 digitos');
      return;
    }
    setState(() => _loading = true);
    final r = await ref.read(authRepositoryProvider).registerVerify(widget.cpf, code);
    setState(() => _loading = false);
    if (!mounted) return;
    switch (r) {
      case RegisterVerifyOk(:final setupToken):
        context.push('/onboarding/password', extra: {
          'setup_token': setupToken,
          'cpf': widget.cpf,
        });
      case RegisterVerifyError(:final message):
        _toast(message);
    }
  }

  Future<void> _resend() async {
    setState(() => _loading = true);
    await ref.read(authRepositoryProvider).registerStart(widget.cpf);
    setState(() => _loading = false);
    if (!mounted) return;
    _toast('Codigo reenviado');
  }

  void _toast(String s) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Confirme seu telefone',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Text(
                'Enviamos um codigo de 6 digitos no WhatsApp ${widget.maskedPhone}.',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: BrandTokens.textSecondary,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceXl),
              TextField(
                controller: _ctrl,
                keyboardType: TextInputType.number,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      letterSpacing: 12,
                      fontWeight: FontWeight.w800,
                    ),
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(6),
                ],
                decoration: const InputDecoration(labelText: 'Codigo'),
              ),
              const Spacer(),
              FilledButton(
                onPressed: _loading ? null : _continue,
                child: _loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Validar codigo'),
              ),
              TextButton(
                onPressed: _loading ? null : _resend,
                child: const Text('Reenviar codigo'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 3: `onboarding_password_screen.dart`**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';

class OnboardingPasswordScreen extends ConsumerStatefulWidget {
  const OnboardingPasswordScreen({
    super.key,
    required this.setupToken,
    required this.cpf,
  });
  final String setupToken;
  final String cpf;

  @override
  ConsumerState<OnboardingPasswordScreen> createState() =>
      _OnboardingPasswordScreenState();
}

class _OnboardingPasswordScreenState
    extends ConsumerState<OnboardingPasswordScreen> {
  final _p1 = TextEditingController();
  final _p2 = TextEditingController();
  bool _loading = false;
  bool _hide = true;

  @override
  void dispose() {
    _p1.dispose();
    _p2.dispose();
    super.dispose();
  }

  Future<void> _continue() async {
    if (_p1.text.length < 8) {
      _toast('Senha deve ter ao menos 8 caracteres');
      return;
    }
    if (_p1.text != _p2.text) {
      _toast('Senhas nao conferem');
      return;
    }
    setState(() => _loading = true);
    final cpfDigits = widget.cpf.replaceAll(RegExp(r'\D'), '');
    final r = await ref.read(authRepositoryProvider).registerPassword(
          setupToken: widget.setupToken,
          password: _p1.text,
          cpfLast4: cpfDigits.substring(cpfDigits.length - 4),
          nome: '',
        );
    setState(() => _loading = false);
    if (!mounted) return;
    switch (r) {
      case AuthOk():
        ref.read(authRefreshProvider).bump();
        context.go('/onboarding/biometric');
      case AuthError(:final message):
        _toast(message);
    }
  }

  void _toast(String s) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Crie uma senha',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Text(
                'No minimo 8 caracteres. Voce vai usar pra entrar no app.',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: BrandTokens.textSecondary,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceXl),
              TextField(
                controller: _p1,
                obscureText: _hide,
                decoration: InputDecoration(
                  labelText: 'Senha',
                  suffixIcon: IconButton(
                    icon: Icon(_hide ? Icons.visibility : Icons.visibility_off),
                    onPressed: () => setState(() => _hide = !_hide),
                  ),
                ),
              ),
              const SizedBox(height: BrandTokens.spaceMd),
              TextField(
                controller: _p2,
                obscureText: _hide,
                decoration: const InputDecoration(labelText: 'Confirme a senha'),
              ),
              const Spacer(),
              FilledButton(
                onPressed: _loading ? null : _continue,
                child: _loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Criar conta'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: `onboarding_biometric_screen.dart`**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_state.dart';
import '../../core/auth/auth_storage.dart';
import '../../core/auth/biometric_service.dart';
import '../../core/branding/brand_tokens.dart';

class OnboardingBiometricScreen extends ConsumerStatefulWidget {
  const OnboardingBiometricScreen({super.key});

  @override
  ConsumerState<OnboardingBiometricScreen> createState() =>
      _OnboardingBiometricScreenState();
}

class _OnboardingBiometricScreenState
    extends ConsumerState<OnboardingBiometricScreen> {
  bool _loading = false;

  Future<void> _enable() async {
    setState(() => _loading = true);
    final svc = ref.read(biometricServiceProvider);
    final ok = await svc.authenticate('Ative pra entrar mais rapido');
    if (ok) {
      await writeBiometricEnabled(true);
      ref.read(authRefreshProvider).bump();
    }
    setState(() => _loading = false);
    if (!mounted) return;
    context.go('/home');
  }

  void _skip() => context.go('/home');

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: BrandTokens.spaceXl),
              Center(
                child: Container(
                  width: 96,
                  height: 96,
                  decoration: BoxDecoration(
                    color: BrandTokens.primary.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(BrandTokens.radiusXl),
                  ),
                  child: const Icon(Icons.fingerprint,
                      size: 56, color: BrandTokens.primary),
                ),
              ),
              const SizedBox(height: BrandTokens.spaceLg),
              Text(
                'Quer entrar com biometria?',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Text(
                'Mais rapido e seguro. Voce ainda pode usar a senha quando quiser.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: BrandTokens.textSecondary,
                    ),
              ),
              const Spacer(),
              FilledButton(
                onPressed: _loading ? null : _enable,
                child: _loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Ativar biometria'),
              ),
              TextButton(
                onPressed: _loading ? null : _skip,
                child: const Text('Agora nao'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 5: Analyze**

```bash
cd apps/cliente-mobile && flutter analyze lib/features/onboarding
```
Expected: 0 issues.

- [ ] **Step 6: Commit**

```bash
git add apps/cliente-mobile/lib/features/onboarding/
git commit -m "feat(cliente-app): onboarding screens (cpf, otp, senha, biometria)"
```

---

## Task 8: Login screen

**Files:**
- Replace stub: `apps/cliente-mobile/lib/features/auth/login_screen.dart`

- [ ] **Step 1: Implementar**

```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _cpfCtrl = TextEditingController();
  final _pwdCtrl = TextEditingController();
  bool _loading = false;
  bool _hide = true;

  @override
  void dispose() {
    _cpfCtrl.dispose();
    _pwdCtrl.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    final cpf = _cpfCtrl.text.replaceAll(RegExp(r'\D'), '');
    if (cpf.length != 11) {
      _toast('Informe um CPF valido');
      return;
    }
    if (_pwdCtrl.text.length < 8) {
      _toast('Senha curta');
      return;
    }
    setState(() => _loading = true);
    final r = await ref.read(authRepositoryProvider).login(
          cpf: cpf,
          password: _pwdCtrl.text,
        );
    setState(() => _loading = false);
    if (!mounted) return;
    switch (r) {
      case AuthOk():
        ref.read(authRefreshProvider).bump();
        context.go('/home');
      case AuthError(:final message):
        _toast(message);
    }
  }

  Future<void> _forgot() async {
    final cpf = _cpfCtrl.text.replaceAll(RegExp(r'\D'), '');
    if (cpf.length != 11) {
      _toast('Informe seu CPF primeiro');
      return;
    }
    setState(() => _loading = true);
    await ref.read(authRepositoryProvider).forgot(cpf);
    setState(() => _loading = false);
    if (!mounted) return;
    _toast('Se o CPF estiver cadastrado, voce recebera um codigo no WhatsApp.');
  }

  void _toast(String s) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Bem-vindo de volta',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Text(
                'Entre com seu CPF e senha.',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: BrandTokens.textSecondary,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceXl),
              TextField(
                controller: _cpfCtrl,
                keyboardType: TextInputType.number,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(11),
                ],
                decoration: const InputDecoration(labelText: 'CPF'),
              ),
              const SizedBox(height: BrandTokens.spaceMd),
              TextField(
                controller: _pwdCtrl,
                obscureText: _hide,
                decoration: InputDecoration(
                  labelText: 'Senha',
                  suffixIcon: IconButton(
                    icon: Icon(_hide ? Icons.visibility : Icons.visibility_off),
                    onPressed: () => setState(() => _hide = !_hide),
                  ),
                ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: _loading ? null : _forgot,
                  child: const Text('Esqueci minha senha'),
                ),
              ),
              const Spacer(),
              FilledButton(
                onPressed: _loading ? null : _login,
                child: _loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Entrar'),
              ),
              TextButton(
                onPressed: _loading ? null : () => context.go('/onboarding/cpf'),
                child: const Text('Criar conta'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Analyze + smoke build**

```bash
cd apps/cliente-mobile && flutter analyze && flutter build apk --debug -t lib/main.dart 2>&1 | tail -10
```
Expected: `Built build/app/outputs/flutter-apk/app-debug.apk`. Se quebrar, inspecionar erro e corrigir antes de commitar.

- [ ] **Step 3: Commit**

```bash
git add apps/cliente-mobile/lib/features/auth/login_screen.dart
git commit -m "feat(cliente-app): tela de login"
```

---

## Pontos de atenção pro executor

1. **Stubs antes do Task 7:** o router (Task 6) referencia 5 telas. Na Task 6 crie todas como `class XxxScreen extends StatelessWidget { const XxxScreen({super.key, ...}); Widget build(_) => const Scaffold(); }` antes de rodar `flutter analyze`. Substitui pelo real nas Tasks 7/8.

2. **`firebase_options.dart` não gerado nessa fase.** O `try/catch` no `main()` lida com isso — app sobe sem push. Geração via `flutterfire configure` fica pra Fase 7.

3. **CPF de teste:** Use o CPF cadastrado no SGP do Robert no celular dele pra testar fluxo real. CPF de demo só funciona se backend tiver mock — não tem.

4. **`flutter build apk --debug`** roda no CI/máquina deploy. Localmente: se Android SDK não estiver setup, **report DONE_WITH_CONCERNS** mas commite mesmo assim — push pra main, watchtower derruba e Robert testa.

5. **Material 3 e cards:** `CardTheme` na versão atual do Flutter usa `CardTheme` (não `CardThemeData`). Se o analyze reclamar de tipo, ajuste pra `CardThemeData(...)` e use `cardTheme: CardThemeData(...)`. Veja o tecnico-mobile/theme.dart pra referência.

6. **Robert testa no celular dele.** Não roda emulador aqui. Cada commit vai pra main → CI builds → ele instala.
