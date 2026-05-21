# cliente-mobile

App Flutter do **cliente final** da Ondeline Telecom — fatura (PIX/boleto), plano, abertura de OS e chat in-app.

Separado do `tecnico-mobile` (app do técnico em campo).

## Setup inicial

Esta pasta foi criada com os sources Dart e o `pubspec.yaml`, mas **não tem os scaffolds nativos** (`android/`, `ios/`). Pra completar:

```bash
cd apps/cliente-mobile
flutter create --org dev.robertbr --project-name cliente_mobile --platforms=android,ios .
flutter pub get
```

Isso preenche `android/` e `ios/` sem mexer no `lib/` que já existe.

## Rodar

```bash
flutter run --dart-define=API_URL=https://apiblabla.robertbr.dev
```

Default já aponta pra prod.

## Build release

```bash
flutter build apk --release
flutter build ipa --release
```
