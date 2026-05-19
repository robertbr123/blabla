# Setup do app Flutter no Mac

Guia passo-a-passo pra rodar o app no seu Mac, em emulador Android e/ou simulador iOS.

> **TL;DR:** instala Flutter SDK + Android Studio, roda `flutter create .` dentro de `apps/tecnico-mobile`, depois `flutter run`. iOS exige Xcode (só Mac mesmo).

---

## 1. Pré-requisitos comuns

```bash
# Homebrew se não tiver
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Git, etc, você já tem
```

## 2. Instalar Flutter SDK

Recomendado: usar **fvm** (Flutter Version Manager) — assim cada projeto roda na versão correta sem brigar com outros.

```bash
brew tap leoafarias/fvm
brew install fvm

# Dentro do projeto:
cd apps/tecnico-mobile
fvm install 3.27.4
fvm use 3.27.4

# Pro `flutter` no PATH apontar pra versão do fvm:
echo 'export PATH="$HOME/fvm/default/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
flutter --version   # → Flutter 3.27.4
```

Alternativa direta (sem fvm):

```bash
brew install --cask flutter
flutter --version
```

Roda o doctor:

```bash
flutter doctor
```

Ele vai listar o que falta. Os 2 itens importantes: **Android toolchain** e **Xcode** (este último só se quiser iOS).

---

## 3. Android (mais rápido pra começar)

### 3.1 Instalar Android Studio

```bash
brew install --cask android-studio
```

Abra Android Studio, ele vai pedir pra baixar:
- **Android SDK** (mais recente)
- **Android SDK Platform-Tools**
- **Android Virtual Device (AVD)**

Aceite tudo. Depois aceite as licenças via CLI:

```bash
flutter doctor --android-licenses
# pressione `y` em todas
```

### 3.2 Criar emulador

Android Studio → **Tools → Device Manager → Create Device**

Recomendado: **Pixel 7** com sistema **Android 14 (API 34)**. ARM image se for Mac M1/M2/M3.

Ligar o emulador antes de rodar o app:

```bash
# Via Android Studio (Device Manager → ▶)
# OU via CLI:
emulator -list-avds              # lista AVDs criados
emulator -avd Pixel_7_API_34 &   # liga em background
```

### 3.3 Bootstrap do app

```bash
cd apps/tecnico-mobile

# 1ª vez: gera android/ (não versionado — .gitignore exclui)
flutter create . --org br.com.ondeline --project-name tecnico_mobile --platforms=android,ios

# Instala deps
flutter pub get

# Gera código Drift (DB local). 1ª vez e a cada mudança em lib/core/db/tables.dart
dart run build_runner build --delete-conflicting-outputs

# Roda no emulador (ou device USB conectado)
flutter run --dart-define=API_URL=http://10.0.2.2:8000
```

> `10.0.2.2` no emulator Android = `localhost` da máquina host. Pro device físico via USB, use o IP da rede local: `--dart-define=API_URL=http://192.168.0.5:8000`.

### 3.4 Hot reload

Com `flutter run` rodando:
- `r` → hot reload (mantém estado, atualiza UI)
- `R` → hot restart (zera estado)
- `q` → sai

---

## 4. iOS (opcional — só Mac)

### 4.1 Xcode

```bash
# Demora bastante (~30min), download de ~7GB
xcode-select --install              # CLI tools
# Pelo App Store:
# 1. Instala "Xcode" do App Store
# 2. Abre uma vez pra aceitar licença
sudo xcodebuild -license accept
sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
```

### 4.2 CocoaPods

```bash
sudo gem install cocoapods
# ou: brew install cocoapods (no Mac novo costuma falhar pelo sistema do Ruby — gem é mais confiável)
```

### 4.3 Simulador iOS

```bash
# Lista simuladores disponiveis
xcrun simctl list devices
# Abre simulador
open -a Simulator
```

### 4.4 Rodar

```bash
cd apps/tecnico-mobile

# Se ainda não fez (passo 3.3), gera ios/:
flutter create . --org br.com.ondeline --project-name tecnico_mobile --platforms=ios

# Patch no Podfile pra silenciar warnings de iOS 9/11 (roda 1x após flutter create):
bash scripts/setup-ios.sh

# CocoaPods (1ª vez ou depois de mudar pubspec):
cd ios && pod install && cd ..

flutter run -d "iPhone 15"   # ou nome que aparece em `flutter devices`
# API URL: simulador iOS compartilha o host real, então:
flutter run --dart-define=API_URL=http://localhost:8000
```

### 4.5 Device físico iOS

- Conecta o iPhone via USB
- iPhone vai pedir "Confiar neste computador" → aceita
- Em Xcode: abre `ios/Runner.xcworkspace`, vai em **Signing & Capabilities**, escolhe seu Team (Apple ID grátis serve pra debug — apps válidos por 7 dias). Bundle ID: `br.com.ondeline.tecnicoMobile`
- `flutter run -d <device>`

---

## 5. Firebase / FCM (push notifications)

Sem isso, o app roda mas não recebe push. Pra dev local, pode pular esta etapa — o `main.dart` ignora Firebase quando não configurado.

### 5.1 Criar projeto Firebase

1. https://console.firebase.google.com → **Add project** → "Ondeline" (ou nome que preferir)
2. Desabilite Google Analytics (não precisamos)
3. Em **Project settings → General**:
   - Botão "Add app" → Android
     - Package: `br.com.ondeline.tecnico_mobile`
     - Baixa `google-services.json`
     - Move pra `apps/tecnico-mobile/android/app/google-services.json`
   - Botão "Add app" → iOS (se for usar)
     - Bundle: `br.com.ondeline.tecnicoMobile`
     - Baixa `GoogleService-Info.plist`
     - Em Xcode: arrasta pro `Runner` (dentro do navigator)

### 5.2 flutterfire (mais fácil)

```bash
dart pub global activate flutterfire_cli
flutterfire configure
# Segue o wizard, escolhe seu projeto Firebase, seleciona android+ios
# Vai gerar lib/firebase_options.dart (ignorado no git, pessoal)
```

Depois disso, edite `lib/main.dart` pra importar:

```dart
import 'firebase_options.dart';

// e troque:
await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
```

### 5.3 Service account pro backend disparar

Em Firebase Console → **Project settings → Service accounts → Generate new private key**.

Baixa um JSON. Esse arquivo vai pro backend como env var (próximo PR fará isso).

---

## 5.5 App icon (BlaBla Twin Ink)

Os assets já estão em `assets/branding/`:

- `app_icon.png` — ícone do app (squircle dark com 2 balões verdes)
- `logo_horizontal_light.png` — wordmark "BlaBla" sobre cream (tela de login modo claro)
- `logo_horizontal_dark.png` — só balões sobre navy (modo escuro)

Pra gerar os ícones nativos Android + iOS a partir do `app_icon.png`:

```bash
cd apps/tecnico-mobile
flutter pub get
dart run flutter_launcher_icons
```

O pacote já está configurado no `pubspec.yaml` (seção `flutter_launcher_icons`). Roda uma vez, depois sempre que mudar `app_icon.png`. Gera os ícones nativos em `android/app/src/main/res/mipmap-*/` e `ios/Runner/Assets.xcassets/AppIcon.appiconset/`.

---

## 6. Comandos do dia-a-dia

```bash
# Dentro de apps/tecnico-mobile:

flutter pub get                                          # instala deps
flutter pub upgrade                                      # atualiza deps
dart run build_runner build --delete-conflicting-outputs # codegen drift
dart run build_runner watch                              # codegen contínuo
flutter analyze --no-fatal-infos                         # lint
flutter test                                             # testes
flutter clean                                            # limpa build/
flutter run                                              # roda no device padrão
flutter run -d <id>                                      # device específico (veja `flutter devices`)
flutter build apk --debug                                # gera APK debug (sem signing)
flutter build apk --release                              # release (precisa signing — ver CI)
flutter build ipa                                        # IPA iOS (precisa Apple Developer)
```

## 7. Troubleshooting

| Sintoma | Solução |
|---|---|
| `flutter doctor` reclama de Android licenses | `flutter doctor --android-licenses` → `y` em tudo |
| `Could not find a suitable JDK` | Instale Java 17: `brew install temurin@17` e `flutter config --jdk-dir $(brew --prefix temurin@17)/libexec/openjdk.jdk/Contents/Home` |
| `CocoaPods not installed` | `sudo gem install cocoapods` |
| `Pod install failed` | `cd ios && rm -rf Pods Podfile.lock && pod install` |
| Emulador Android trava | Crie um device com perfil ARM64 (M1/M2/M3 Macs não rodam x86 bem) |
| `Hot reload` não pega | `R` (hot restart) ou `flutter clean && flutter run` |
| `MissingPluginException` | Mudou plugin nativo: `flutter clean`, depois `cd ios && pod install && cd ..` e `flutter run` |
| App não conecta na API local | Android emulator usa `10.0.2.2:8000`, iOS simulator usa `localhost:8000`, device físico usa IP da rede |

## 8. Como vou rodar AGORA (resumo Mac → Android)

```bash
# 1. Instala Flutter (se ainda não)
brew install --cask flutter
flutter doctor

# 2. Instala Android Studio + cria emulador (Pixel 7 API 34)
brew install --cask android-studio
# (abre o app, baixa SDK + cria AVD via Device Manager)
flutter doctor --android-licenses

# 3. Bootstrap do app
cd apps/tecnico-mobile
flutter create . --org br.com.ondeline --project-name tecnico_mobile
flutter pub get
dart run build_runner build --delete-conflicting-outputs

# 4. Liga emulador (Android Studio Device Manager → ▶) e roda
flutter run --dart-define=API_URL=http://10.0.2.2:8000

# 5. (Opcional) iOS depois:
# Instala Xcode pelo App Store, sudo xcodebuild -license accept
# sudo gem install cocoapods
# cd ios && pod install && cd ..
# flutter run -d "iPhone 15"
```

> Depois do `flutter create .`, os diretórios `android/` e `ios/` ficam no seu disco mas **não vão pro git** (estão no `.gitignore`). O CI faz `flutter create .` toda vez também — é o padrão de monorepo Flutter.

---

## 9. APK release com signing (CI)

O CI gera APK debug automaticamente. O **release com signing** roda só em push pra `main` E se os 4 secrets estiverem configurados:

| Secret | Como gerar |
|---|---|
| `ANDROID_KEYSTORE_B64` | `base64 -i release.keystore \| pbcopy` (no Mac) |
| `ANDROID_KEYSTORE_PASSWORD` | senha da keystore |
| `ANDROID_KEY_ALIAS` | alias da chave (ex: `ondeline`) |
| `ANDROID_KEY_PASSWORD` | senha da chave (pode ser igual à da keystore) |
| `MOBILE_API_URL` *(opcional)* | URL de prod da API (default: `https://api.ondeline.dev`) |

### Gerar a keystore (uma vez só, **guarda em local seguro!**)

```bash
keytool -genkey -v \
  -keystore release.keystore \
  -alias ondeline \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -dname "CN=Ondeline, O=Ondeline Telecom, C=BR"
# Vai pedir 2 senhas. Anota.
```

⚠️ **Se você perder a keystore, perde a capacidade de publicar updates do app**. Faça backup off-site (Bitwarden/1Password/cofre offline).

### Configurar no GitHub

```bash
# Encode pra base64 (Mac):
base64 -i release.keystore | pbcopy
# Cola em: GitHub repo → Settings → Secrets and variables → Actions → New secret
# Nome: ANDROID_KEYSTORE_B64
# Repete pros outros 3 secrets.
```

Depois do próximo push pra main, o job `mobile` produz `tecnico-mobile-release-apk` como artifact (30 dias retenção).

### Próximo nível: Play Store

Pra publicar automaticamente: adicionar `fastlane` ou usar a [Google Play API](https://github.com/r0adkll/upload-google-play). Fica pra depois.
