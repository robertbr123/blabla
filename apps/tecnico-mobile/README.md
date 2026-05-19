# Técnico Mobile (Flutter)

App nativo Android/iOS para os técnicos da Ondeline. Substitui o PWA Next.js (`apps/tecnico-pwa`) quando estiver completo.

## Por que Flutter

- **Offline real**: SQLite + outbox sync. Técnico em campo sem sinal continua trabalhando — fotos, conclusões e GPS ficam em fila e sobem quando reconecta.
- **Push FCM nativo**: notificação de nova OS atribuída mesmo com app fechado (web push iOS é instável).
- **Câmera + GPS sem dor**: permissões nativas, foto antes/depois, GPS contínuo do trajeto.
- **Performance**: scroll suave, animações nativas, splash, ícone — sensação de app de verdade.

## Stack

| Camada | Lib |
|---|---|
| HTTP | dio |
| State | flutter_riverpod |
| Nav | go_router |
| DB local | drift + sqlite3 |
| Auth storage | flutter_secure_storage |
| Push | firebase_messaging + flutter_local_notifications |
| Câmera | image_picker |
| GPS | geolocator |
| Permissões | permission_handler |

## Estrutura

```
lib/
├── main.dart                        — bootstrap + router
├── core/
│   ├── api/
│   │   ├── api_client.dart          — Dio + JWT interceptor
│   │   └── endpoints.dart
│   ├── auth/
│   │   ├── auth_repository.dart     — login/logout/me
│   │   └── auth_storage.dart        — secure storage do token
│   ├── db/
│   │   ├── database.dart            — drift schema (OS + outbox)
│   │   └── tables.dart
│   ├── sync/
│   │   └── sync_service.dart        — fila offline + reenvio
│   └── theme.dart
├── features/
│   ├── auth/
│   │   └── login_screen.dart
│   └── os/
│       ├── os_list_screen.dart
│       ├── os_detail_screen.dart
│       └── widgets/
│           └── os_card.dart
└── router.dart
```

## Setup local (primeira vez)

```bash
# 1. Instala Flutter SDK (https://docs.flutter.dev/get-started/install)
flutter doctor

# 2. Dentro de apps/tecnico-mobile, gera os bindings nativos:
cd apps/tecnico-mobile
flutter create . --org br.com.ondeline --project-name tecnico_mobile
# (Isso cria as pastas android/ e ios/ vazias. Não sobrescreve lib/.)

# 3. Instala deps
flutter pub get

# 4. Gera código drift (DB local)
dart run build_runner build --delete-conflicting-outputs

# 5. Configura API URL via --dart-define no run:
flutter run --dart-define=API_URL=https://api.ondeline.dev
```

## Configuração Firebase (FCM)

1. Cria projeto em https://console.firebase.google.com
2. Adiciona apps Android e iOS:
   - Android package: `br.com.ondeline.tecnico_mobile`
   - iOS bundle: `br.com.ondeline.tecnicoMobile`
3. Baixa `google-services.json` → `android/app/`
4. Baixa `GoogleService-Info.plist` → `ios/Runner/`
5. Roda `flutterfire configure` (https://firebase.google.com/docs/flutter/setup)

## Endpoints backend usados

Já existem (autenticação como técnico):

- `POST /auth/login` — login
- `GET /auth/me` — perfil
- `GET /api/v1/tecnico/me/os` — OSs atribuídas
- `POST /api/v1/tecnico/me/os/{id}/iniciar` — iniciar visita (GPS)
- `POST /api/v1/tecnico/me/os/{id}/concluir` — concluir
- `POST /api/v1/tecnico/me/os/{id}/foto` — upload foto

A criar (próximos PRs):

- `POST /api/v1/tecnico/me/fcm-token` — registra FCM token do dispositivo
- `POST /api/v1/tecnico/me/fcm-token/revoke` — revoga no logout

## Roadmap

- [x] Scaffold de pastas + pubspec
- [x] Auth flow (login + token storage)
- [x] Lista de OS + detalhe (online)
- [ ] Drift DB com OS cached + outbox table
- [ ] Sync service (background fetch + retry)
- [ ] Câmera antes/depois
- [ ] GPS contínuo durante visita (track trajeto)
- [ ] FCM push: nova OS, OS reaberta
- [ ] Estoque do técnico (offline)
- [ ] Checklist de conclusão (offline)
- [ ] Tema dark
- [ ] Splash + ícone
- [ ] CI: `flutter build apk --release`
- [ ] Deploy: GitHub Actions + Play Store / TestFlight

## Testar API local sem deploy

```bash
# Backend rodando em http://localhost:8000
flutter run --dart-define=API_URL=http://10.0.2.2:8000  # Android emulator
flutter run --dart-define=API_URL=http://localhost:8000 # iOS simulator
```

## CI

`.github/workflows/ci.yml` tem um job `mobile` que:

1. Faz checkout
2. Instala Java 17 + Flutter 3.24.5 stable
3. Roda `flutter create .` (gera android/ na hora — não versionado)
4. `flutter pub get`
5. `dart run build_runner build` (drift codegen)
6. `flutter analyze --no-fatal-infos`
7. `flutter test`
8. `flutter build apk --debug` + sobe artifact `tecnico-mobile-debug-apk` (retenção 14 dias)

APK release virá num PR futuro quando configurarmos signing key como secret.

## Rodar testes localmente

```bash
cd apps/tecnico-mobile
flutter pub get
dart run build_runner build --delete-conflicting-outputs
flutter test
```
