#!/usr/bin/env bash
# Release iOS do app cliente — build + fix do ITMS-90111 + export assinado.
#
# O Flutter carimba o App.framework com sdk 13.0 (hardcoded na ferramenta) e a
# Apple exige SDK iOS 26+ em TODOS os binários do pacote desde 2026-04-28.
# Este script: builda o ipa, re-estampa o App.framework via vtool dentro do
# xcarchive e re-exporta (o export re-assina tudo oficialmente).
#
# Uso: ./scripts/release_ios.sh   (na raiz do apps/cliente-mobile)
# Saída: build/ios/ipa_release/cliente_mobile.ipa
set -euo pipefail

SDK_ALVO="${SDK_ALVO:-26.5}"   # atualizar quando o SDK do Xcode mudar
MINOS="${MINOS:-15.0}"

echo "==> flutter build ipa --release"
flutter build ipa --release

APP="build/ios/archive/Runner.xcarchive/Products/Applications/Runner.app/Frameworks/App.framework/App"
echo "==> re-estampando App.framework (minos $MINOS, sdk $SDK_ALVO)"
vtool -set-build-version ios "$MINOS" "$SDK_ALVO" -replace -output "$APP" "$APP"

echo "==> re-exportando (re-assina)"
rm -rf build/ios/ipa_release
xcodebuild -exportArchive \
  -archivePath build/ios/archive/Runner.xcarchive \
  -exportPath build/ios/ipa_release \
  -exportOptionsPlist build/ios/ipa/ExportOptions.plist

IPA="build/ios/ipa_release/cliente_mobile.ipa"
echo "==> varredura de SDK de todos os binários:"
TMP=$(mktemp -d)
unzip -qo "$IPA" -d "$TMP"
FALHA=0
while IFS= read -r f; do
  if file "$f" | grep -q "Mach-O"; then
    sdk=$(vtool -show-build "$f" 2>/dev/null | awk '/sdk/{print $2; exit}')
    printf "  sdk=%-6s %s\n" "$sdk" "${f#"$TMP"/}"
    # falha se sdk < 26
    major="${sdk%%.*}"
    if [ -n "$major" ] && [ "$major" -lt 26 ]; then FALHA=1; fi
  fi
done < <(find "$TMP" -type f)
rm -rf "$TMP"

if [ "$FALHA" -eq 1 ]; then
  echo "ERRO: binário com SDK < 26 no pacote — NÃO subir pra App Store." >&2
  exit 1
fi
echo "==> OK: $IPA pronto pro Transporter ✅"
