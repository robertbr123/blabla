#!/usr/bin/env bash
# Define o display name do app (o que aparece embaixo do icone) como "Ondeline".
# Rodar DEPOIS de `flutter create --org dev.robertbr --project-name cliente_mobile --platforms=android,ios .`
#
# Uso: bash scripts/set-display-name.sh
set -euo pipefail

cd "$(dirname "$0")/.."

ANDROID_MANIFEST="android/app/src/main/AndroidManifest.xml"
IOS_PLIST="ios/Runner/Info.plist"
DISPLAY_NAME="Ondeline"

if [ ! -f "$ANDROID_MANIFEST" ]; then
  echo "ERRO: $ANDROID_MANIFEST nao encontrado. Rode 'flutter create .' primeiro." >&2
  exit 1
fi
if [ ! -f "$IOS_PLIST" ]; then
  echo "ERRO: $IOS_PLIST nao encontrado. Rode 'flutter create .' primeiro." >&2
  exit 1
fi

# Android — troca android:label="cliente_mobile" por "Ondeline"
sed -i.bak "s|android:label=\"cliente_mobile\"|android:label=\"$DISPLAY_NAME\"|g" "$ANDROID_MANIFEST"
rm -f "$ANDROID_MANIFEST.bak"
echo "OK  $ANDROID_MANIFEST -> android:label=\"$DISPLAY_NAME\""

# iOS — usa PlistBuddy se disponivel (macOS), senao cai em sed
if [ -x /usr/libexec/PlistBuddy ]; then
  /usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName $DISPLAY_NAME" "$IOS_PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string $DISPLAY_NAME" "$IOS_PLIST"
  echo "OK  $IOS_PLIST -> CFBundleDisplayName=$DISPLAY_NAME (via PlistBuddy)"
else
  # Fallback: troca <string>cliente_mobile</string> generico (afeta CFBundleName e DisplayName)
  sed -i.bak "s|<string>cliente_mobile</string>|<string>$DISPLAY_NAME</string>|g" "$IOS_PLIST"
  rm -f "$IOS_PLIST.bak"
  echo "OK  $IOS_PLIST -> $DISPLAY_NAME (via sed fallback)"
fi

echo ""
echo "Pronto. Commite os 2 arquivos:"
echo "  git add $ANDROID_MANIFEST $IOS_PLIST"
echo "  git commit -m 'feat(cliente-app): display name = Ondeline'"
