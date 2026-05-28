# Release workflow — Play Store (automação de notas)

## Estado atual (depois do commit da Fase 3.3)

Quando você cria uma tag `vX.Y.Z` no Git e dá push:

```bash
git tag v1.0.1
git push origin v1.0.1
```

…o workflow `.github/workflows/release.yml` automaticamente:

1. Gera um **CHANGELOG** a partir dos commits desde a tag anterior (usando convenção `feat: fix: chore:` etc).
2. Cria um **GitHub Release** com esse changelog como release notes.
3. Anexa o changelog ao **Job Summary** do workflow run pra você copiar fácil.

**O que isso resolve:** você nunca mais escreve nota de versão à mão. Cria a tag, o GitHub gera a nota.

**O que ainda é manual:** copiar essa nota do GitHub Release pro campo "What's new in this version" na Play Console.

## Convenção de commits (que vira o changelog)

| Prefixo | Vira | Aparece como |
|---------|------|--------------|
| `feat:` | 🚀 Features | grande destaque |
| `fix:` | 🐛 Bug Fixes | destaque |
| `perf:` | ⚡ Performance | destaque |
| `refactor:` | ♻️ Refactor | seção menor |
| `docs:` | 📚 Docs | seção menor |
| `test:` | 🧪 Tests | seção menor |
| `chore:` | 🔧 Chore | seção menor |
| `wip:`, `Merge ...` | (filtrado) | não aparece |

Exemplo de bom commit pro changelog:
```
feat(cliente-mobile): NPS em tela cheia depois de OS concluida

Antes era bottom-sheet pequeno; agora ocupa toda a tela com animacao
de entrada. Aumenta taxa de resposta em ~30% nos testes internos.
```

## Próximo passo (opcional): automação total via Google Play API

Pra deixar 100% automatizado (subir AAB + notas direto pra Play sem clicar nada), precisa:

### 1. Criar Service Account no Google Cloud

1. Acesse https://console.cloud.google.com → seu projeto.
2. **IAM & Admin → Service Accounts → CREATE SERVICE ACCOUNT**.
3. Nome: `play-publisher`. Pula as roles.
4. Após criar → **KEYS → ADD KEY → Create new key → JSON** → baixa o arquivo `.json`.

### 2. Conectar com a Play Console

1. https://play.google.com/console → **Setup → API access**.
2. Vincula seu projeto Google Cloud (já deve aparecer).
3. Na lista de Service Accounts, acha o `play-publisher@...` → **Grant access**.
4. Permissões mínimas: **Releases → Manage testing track releases** (e production se quiser).

### 3. Adicionar o JSON como GitHub Secret

1. https://github.com/SEU_USER/SEU_REPO/settings/secrets/actions
2. **New repository secret**:
   - Name: `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`
   - Value: cole o conteúdo do `.json` inteiro

### 4. Descomentar o step no workflow

Em `.github/workflows/release.yml`, depois do bloco `- name: Summary`, descomente algo como:

```yaml
- name: Build AAB (opcional — só se quiser CI buildar)
  uses: subosito/flutter-action@v2
  # ... config do Flutter aqui ...

- name: Upload to Google Play
  uses: r0adkll/upload-google-play@v1
  with:
    serviceAccountJsonPlainText: ${{ secrets.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON }}
    packageName: dev.robertbr.cliente_mobile
    releaseFiles: apps/cliente-mobile/build/app/outputs/bundle/release/app-release.aab
    track: internal     # mude pra production quando pronto
    whatsNewDirectory: distribution/whatsnew
    status: completed
```

**Por que ainda está comentado:** hoje você **builda o AAB localmente** (com a keystore do seu Mac). Pra mover o build pro CI:
- Precisa subir a keystore como secret (`SIGNING_KEYSTORE_BASE64`) **ou** usar Play App Signing puro (upload key no CI, app signing no Google).
- Adicionar Flutter setup no workflow (Java + Flutter SDK).
- Configurar `key.properties` no runner via secrets.

É um setup mais robusto mas leva ~1 dia pra zerar. Quando você quiser fazer, abre o doc e me diz que eu adapto.

## App Store (iOS) — paralelo

A Apple tem uma API parecida (App Store Connect API com `.p8` key) e a action `apple-actions/upload-testflight-build@v1` ou similar. Mesma estrutura — quando quiser, monto o workflow espelho pra iOS.

## Resumo: o que cada tag faz hoje

```
git tag v1.0.1 && git push origin v1.0.1
        ↓
   GitHub Actions roda release.yml
        ↓
   ├─ Gera CHANGELOG dos commits desde v1.0.0
   ├─ Cria GitHub Release com a nota
   └─ Mostra no Summary do run
        ↓
   Você copia a nota pro Play Console manualmente (por enquanto)
```

A automação total Play requer setup de Service Account (~30min) — quando bater a vontade, segue a seção 1-4 acima.
