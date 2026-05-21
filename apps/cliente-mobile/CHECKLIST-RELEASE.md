# Checklist de release — cliente-mobile

Passos pra publicar nas stores (Google Play + App Store).

## 1. Ícone do app

Gera os tamanhos automaticamente com `flutter_launcher_icons`:

```bash
flutter pub add --dev flutter_launcher_icons
```

Adiciona em `pubspec.yaml`:

```yaml
flutter_launcher_icons:
  android: true
  ios: true
  image_path: "assets/icon/icon.png"          # 1024x1024
  adaptive_icon_background: "#3A2A6B"          # roxo Ondeline
  adaptive_icon_foreground: "assets/icon/foreground.png"
  min_sdk_android: 21
```

Coloca:
- `assets/icon/icon.png` — 1024x1024, ícone completo (PNG transparente)
- `assets/icon/foreground.png` — 1024x1024, só a marca (sem fundo)

Roda:

```bash
flutter pub get
dart run flutter_launcher_icons
```

## 2. Display name

Já feito. Veja `scripts/set-display-name.sh`.

## 3. Push notifications

Geração do `firebase_options.dart`:

```bash
dart pub global activate flutterfire_cli
flutterfire configure --project=<projeto-firebase-id>
```

Selecione Android + iOS. O comando cria `lib/firebase_options.dart` (gitignored). Sem isso, push fica desabilitado mas app sobe normal.

## 4. Splash nativo

Pra evitar tela branca antes do Flutter carregar, use `flutter_native_splash`:

```yaml
flutter_native_splash:
  color: "#3A2A6B"
  image: assets/icon/splash.png
  android_12:
    image: assets/icon/splash.png
    color: "#3A2A6B"
```

```bash
dart run flutter_native_splash:create
```

## 5. App Store / TestFlight (iOS)

Pré-requisitos:
- Apple Developer Account ativa ($99/ano)
- Xcode 16+
- Provisioning Profile + App ID `dev.robertbr.clienteMobile`

Build:

```bash
flutter build ipa --release \
  --dart-define=API_URL=https://apiblabla.robertbr.dev
```

Resultado em `build/ios/ipa/cliente_mobile.ipa`.

Upload via Transporter ou:

```bash
xcrun altool --upload-app -f build/ios/ipa/cliente_mobile.ipa \
  -u <apple-id> -p <app-specific-password>
```

## 6. Google Play

Pré-requisitos:
- Google Play Console ($25 uma vez)
- Keystore de assinatura

Gera keystore (uma vez):

```bash
keytool -genkey -v -keystore ~/cliente-mobile-key.jks \
  -keyalg RSA -keysize 2048 -validity 10000 -alias cliente_mobile
```

Cria `android/key.properties` (NÃO commitar):

```
storePassword=<senha>
keyPassword=<senha>
keyAlias=cliente_mobile
storeFile=/Users/robertalbino/cliente-mobile-key.jks
```

Em `android/app/build.gradle` adicionar bloco signing (se não vier no template):

```gradle
def keystoreProperties = new Properties()
def keystorePropertiesFile = rootProject.file('key.properties')
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}

android {
    signingConfigs {
        release {
            keyAlias keystoreProperties['keyAlias']
            keyPassword keystoreProperties['keyPassword']
            storeFile keystoreProperties['storeFile'] ? file(keystoreProperties['storeFile']) : null
            storePassword keystoreProperties['storePassword']
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
        }
    }
}
```

Build:

```bash
flutter build appbundle --release \
  --dart-define=API_URL=https://apiblabla.robertbr.dev
```

Resultado: `build/app/outputs/bundle/release/app-release.aab`. Upload na Play Console.

## 7. Privacidade na ficha das stores

Tanto a Play Store quanto a App Store exigem declaração de dados coletados. Use o conteudo de `lib/features/legal/legal_screen.dart` (constantes `termosUsoBody` e `politicaPrivacidadeBody`) como referência. Hospede a politica em URL publica (ex: ondelinetelecom.com.br/privacidade) — exigido pela App Store.

Declarar:
- **Identificadores**: nome, CPF (sensível!), telefone, email — para autenticação e suporte
- **Histórico de compras**: status de faturas — para funcionalidade do app
- **Diagnósticos**: opcional, só se ativar Sentry/Crashlytics

## 8. Screenshots

Tamanhos exigidos:
- **App Store**: 6.7" iPhone (iPhone 15 Pro Max) + 5.5" iPhone (iPhone 8 Plus). Mínimo 3, recomendado 5.
- **Play Store**: 16:9 phone (mínimo 2), 7" tablet (opcional), 10" tablet (opcional)

Roda no simulador maior, navega pelas telas chave, salva screenshots:
- Home com hero card
- Faturas (lista + bottom sheet aberto)
- Suporte (chat com algumas msgs)
- Wizard de novo chamado
- Perfil

## 9. Descrição da ficha

```
Ondeline — sua internet na palma da mao.

• Veja seu plano e historico de faturas
• Copie o PIX ou abra o boleto em 2 toques
• Abra um chamado direto pelo app: internet lenta, mudanca de endereco, troca de plano
• Converse com nosso assistente virtual
• Tudo seguro: senha + biometria + autenticacao por WhatsApp
```

## 10. Antes de subir pra producao

- [ ] Testar fluxo completo de cadastro com CPF real
- [ ] Confirmar que push notifications chegam (após `firebase_options.dart` gerado)
- [ ] Confirmar que excluir conta funciona end-to-end
- [ ] Confirmar links de Termos e Privacidade abrem
- [ ] Confirmar que tema escuro funciona em todas as telas
- [ ] Verificar que o display name é "Ondeline" embaixo do icone
- [ ] Verificar que `API_URL` aponta pra prod
- [ ] Versão bumpada em `pubspec.yaml` (`version: 0.1.0+1` → `1.0.0+1` antes de publicar)
