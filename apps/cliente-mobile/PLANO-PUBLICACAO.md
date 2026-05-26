# Plano de Publicação — Ondeline (cliente-mobile)

Plano acionável pra publicar na **Google Play** e **App Store**, com o que foi
**verificado no código** (não só documentado). Complementa o `CHECKLIST-RELEASE.md`.

> Status verificado em 2026-05-26 contra o código atual.

---

## 0. Estado atual (auditoria do código)

| Item | Status | Onde |
|------|--------|------|
| Push Android (FCM) | ✅ funcionando (testado no aparelho) | `push_service.dart`, `google-services.json` |
| Exclusão de conta in-app (Apple exige) | ✅ existe | `perfil_screen.dart:182`, `me_repository.deleteMe()` |
| Display name "Ondeline" | ✅ Android + iOS | `AndroidManifest`, `Info.plist` |
| Ícone do app configurado | ✅ `flutter_launcher_icons` | `assets/icon/icon.png` (1024) |
| `GoogleService-Info.plist` (iOS) | ✅ presente | `ios/Runner/` |
| API_URL via dart-define | ✅ default = prod | `api_client.dart:6` |
| **Assinatura release Android** | ❌ **usa chave de DEBUG** | `build.gradle.kts:41` — **BLOQUEADOR** |
| **Versão do app** | ⚠️ `0.1.0+1` | precisa virar `1.0.0+1` |
| **`NSFaceIDUsageDescription` (iOS)** | ❌ **ausente** | `Info.plist` — **crasha Face ID** |
| **Push iOS (APNs)** | ❌ **não configurado** | sem entitlements/capability/AppDelegate |
| Orientação travada em retrato | ⚠️ iOS permite landscape | `Info.plist` |
| Podfile platform iOS | ⚠️ comentado `# platform :ios, '13.0'` | `ios/Podfile:2` |
| Splash nativo (anti tela branca) | ⚠️ não configurado | opcional |

**Resumo:** Android tem **1 bloqueador** (assinatura). iOS tem **2 bloqueadores**
(Face ID string + APNs) e precisa de setup de capabilities no Xcode.

---

## 1. BLOQUEADORES — resolver antes de qualquer build de release

### 1.1 Android — assinatura de release (hoje está com chave debug)

O `build.gradle.kts:41` está com `signingConfig = signingConfigs.getByName("debug")`.
A Play Store **rejeita** APK/AAB assinado com debug.

**Passo 1 — gerar keystore (uma vez, guardar com a vida):**
```bash
keytool -genkey -v -keystore ~/cliente-mobile-key.jks \
  -keyalg RSA -keysize 2048 -validity 10000 -alias cliente_mobile
```

**Passo 2 — criar `android/key.properties` (NÃO commitar):**
```properties
storePassword=<senha>
keyPassword=<senha>
keyAlias=cliente_mobile
storeFile=/Users/robertalbino/cliente-mobile-key.jks
```

**Passo 3 — config no `build.gradle.kts`** (ATENÇÃO: o `CHECKLIST-RELEASE.md`
mostra sintaxe Groovy; o arquivo é **Kotlin DSL**, então é assim):
```kotlin
import java.util.Properties
import java.io.FileInputStream

val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("key.properties")
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
}

android {
    // ...
    signingConfigs {
        create("release") {
            keyAlias = keystoreProperties["keyAlias"] as String
            keyPassword = keystoreProperties["keyPassword"] as String
            storeFile = file(keystoreProperties["storeFile"] as String)
            storePassword = keystoreProperties["storePassword"] as String
        }
    }
    buildTypes {
        getByName("release") {
            signingConfig = signingConfigs.getByName("release")
        }
    }
}
```

> ⚠️ **Backup do `.jks` + senhas.** Perdeu a keystore = não consegue mais
> atualizar o app na Play (só publicando app novo). Guarde em gerenciador de
> senhas + backup offline.

### 1.2 iOS — `NSFaceIDUsageDescription` (sem isso o app crasha na biometria)

O app usa `local_auth` (`biometric_service.dart`). No iOS, usar Face ID **sem**
essa chave no `Info.plist` derruba o app. Adicionar:
```xml
<key>NSFaceIDUsageDescription</key>
<string>Usamos o Face ID para você entrar com segurança e rapidez.</string>
```

### 1.3 iOS — Push (APNs) não está configurado

Push no iOS **não passa pelo FCM direto** — precisa de APNs. Hoje falta tudo:

1. **Apple Developer → Keys:** criar uma **APNs Auth Key** (.p8). Subir no
   **Firebase Console → Project Settings → Cloud Messaging → Apple app**.
2. **Xcode → Runner → Signing & Capabilities:** adicionar
   **Push Notifications** e **Background Modes → Remote notifications**.
   Isso gera o `Runner.entitlements` com `aps-environment`.
3. **AppDelegate.swift:** registrar pra remote notifications e ligar o APNs token
   ao Firebase (`FirebaseApp.configure()` / `Messaging.apnsToken`). Hoje o
   AppDelegate só registra plugins.

> Sem isso, o app iOS **roda normal**, mas push não chega. Dá pra publicar a v1
> iOS sem push e ligar depois — **decisão sua**. Se publicar sem, tire as
> promessas de notificação da descrição da loja.

---

## 2. Versão e configuração comum

- [ ] Bump em `pubspec.yaml`: `version: 0.1.0+1` → **`1.0.0+1`**.
- [ ] Confirmar `API_URL` = prod (`https://apiblabla.robertbr.dev` já é o default).
- [ ] (Recomendado) Travar orientação em **retrato**: no `Info.plist` deixar só
      `UIInterfaceOrientationPortrait` (o app é desenhado pra retrato).
- [ ] (Recomendado) Descomentar `platform :ios, '13.0'` no `ios/Podfile` e rodar
      `cd ios && pod install`.
- [ ] (Opcional) Splash nativo com `flutter_native_splash` pra matar o flash
      branco (passo 4 do `CHECKLIST-RELEASE.md`).

---

## 3. Google Play — passo a passo

**Pré-requisitos:** conta Google Play Console ($25 uma vez), keystore (passo 1.1).

1. [ ] Resolver bloqueador 1.1 (assinatura).
2. [ ] Build do bundle:
   ```bash
   flutter build appbundle --release \
     --dart-define=API_URL=https://apiblabla.robertbr.dev
   ```
   Saída: `build/app/outputs/bundle/release/app-release.aab`.
3. [ ] Play Console → criar app → preencher ficha (descrição no passo 9 do
   checklist), categoria, contato.
4. [ ] **Data safety form**: declarar nome, **CPF (sensível)**, telefone, email,
   status de faturas. Marcar criptografia em trânsito + opção de exclusão.
5. [ ] Política de privacidade em **URL pública** (ex:
   `ondelinetelecom.com.br/privacidade`).
6. [ ] Screenshots (passo 8 do checklist): mínimo 2 phone.
7. [ ] Upload do `.aab` em **Teste interno** primeiro → instalar via link →
   validar fluxo real → depois promover pra **Produção**.

---

## 4. App Store — passo a passo

**Pré-requisitos:** Apple Developer ($99/ano), Xcode 16+, Mac.

1. [ ] Resolver bloqueadores 1.2 (Face ID) e decidir sobre 1.3 (push).
2. [ ] App Store Connect → criar app com Bundle ID `dev.robertbr.clienteMobile`.
3. [ ] Build do IPA:
   ```bash
   flutter build ipa --release \
     --dart-define=API_URL=https://apiblabla.robertbr.dev
   ```
4. [ ] Upload via **Transporter** (mais simples) ou `xcrun altool`.
5. [ ] **App Privacy** (nutrition label): mesmos dados do passo 4 do Play.
   CPF entra como identificador sensível.
6. [ ] **URL de política de privacidade** (obrigatória — App Store é mais rígida).
7. [ ] Screenshots 6.7" (iPhone 15 Pro Max) — obrigatório.
8. [ ] Distribuir pro **TestFlight** primeiro, instalar, validar → submeter pra
   review.

### Pontos de atenção na review da Apple
- ✅ **Exclusão de conta in-app** já existe (a Apple checa isso — Guideline 5.1.1).
- ⚠️ **Login demo/credencial de teste:** a Apple precisa entrar no app. Como o
  login é por CPF + OTP via WhatsApp, **forneça uma conta de teste** (CPF + como
  receber o código) no campo "Notes" da review, ou um bypass de OTP pra um CPF
  específico. Sem isso, a review é rejeitada por "não conseguimos acessar".
- ⚠️ Se publicar **sem push** (1.3 adiado), não mencione notificações na ficha.

---

## 5. Checklist final (do `CHECKLIST-RELEASE.md`, revalidar)

- [ ] Cadastro com CPF real end-to-end
- [ ] Push chega (Android ✅ / iOS depende de 1.3)
- [ ] Excluir conta funciona end-to-end ✅ (existe)
- [ ] Termos e Privacidade abrem
- [ ] Tema escuro em todas as telas
- [ ] Display name "Ondeline" embaixo do ícone
- [ ] `API_URL` = prod
- [ ] Versão = `1.0.0+1`

---

## 6. Ordem sugerida (caminho mais curto até a loja)

1. **Android primeiro** (menos atrito): resolver 1.1 → bump versão → build AAB →
   teste interno → produção. Dá pra publicar **esta semana**.
2. **iOS em paralelo/depois:** resolver 1.2 (rápido) → decidir 1.3 (push: ligar
   agora ou v1.1) → setup Xcode → TestFlight → review (com conta de teste).

> Eu posso aplicar agora os itens de código (1.1 assinatura em Kotlin DSL, 1.2
> Face ID, bump de versão, travar retrato, Podfile). O 1.3 (APNs) e a geração da
> keystore exigem você (Apple/Google consoles + senha do keystore) — esses eu te
> guio passo a passo.
