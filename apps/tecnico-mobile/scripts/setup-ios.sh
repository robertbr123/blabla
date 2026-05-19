#!/usr/bin/env bash
# Patches no projeto iOS gerado pelo `flutter create .`.
# Roda DEPOIS do flutter create + pub get, ANTES do pod install.
#
# O que faz:
# 1. Sobe IPHONEOS_DEPLOYMENT_TARGET pra 13.0 no Podfile (silencia warnings
#    de pods que estavam fixados em 9.0/11.0)
# 2. Adiciona um post_install no Podfile pra propagar pro Pods.xcodeproj
#
# Uso (do diretorio apps/tecnico-mobile):
#   bash scripts/setup-ios.sh
#   cd ios && pod install && cd ..
#   flutter run -d <device>

set -euo pipefail
cd "$(dirname "$0")/.."

PODFILE="ios/Podfile"
if [ ! -f "$PODFILE" ]; then
  echo "✗ $PODFILE não existe. Roda 'flutter create . --platforms=ios' primeiro."
  exit 1
fi

# Bump platform :ios, '12.0' (ou superior) — descomentar se estiver commentado.
if grep -qE "^# platform :ios" "$PODFILE"; then
  sed -i.bak "s/^# platform :ios.*/platform :ios, '13.0'/" "$PODFILE"
  echo "✓ Descomentei platform :ios e setei 13.0"
elif grep -qE "^platform :ios" "$PODFILE"; then
  sed -i.bak "s/^platform :ios.*/platform :ios, '13.0'/" "$PODFILE"
  echo "✓ Atualizei platform :ios pra 13.0"
fi

# Adiciona post_install que propaga IPHONEOS_DEPLOYMENT_TARGET=13.0 pros pods.
if ! grep -q "IPHONEOS_DEPLOYMENT_TARGET = '13.0'" "$PODFILE"; then
  # Encontra o ultimo `end` do arquivo e injeta antes.
  python3 <<'PY'
import re, pathlib
path = pathlib.Path('ios/Podfile')
src = path.read_text()

block = """
post_install do |installer|
  installer.pods_project.targets.each do |target|
    flutter_additional_ios_build_settings(target)
    target.build_configurations.each do |config|
      config.build_settings['IPHONEOS_DEPLOYMENT_TARGET'] = '13.0'
    end
  end
end
"""

if "post_install" in src:
    # Substitui o post_install existente
    src = re.sub(
        r"post_install do \|installer\|.*?end\nend",
        block.strip(),
        src,
        flags=re.DOTALL,
    )
else:
    src = src.rstrip() + "\n" + block

path.write_text(src)
print("✓ post_install patched")
PY
fi

rm -f "$PODFILE.bak"
echo "✓ Setup iOS OK. Agora roda: cd ios && pod install && cd .. && flutter run"
