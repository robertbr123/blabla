#!/usr/bin/env bash
# Patches no projeto iOS gerado pelo `flutter create .`.
# Roda DEPOIS do flutter create + pub get, ANTES do pod install.
#
# O que faz:
# 1. Sobe IPHONEOS_DEPLOYMENT_TARGET pra 13.0 no Podfile (silencia warnings)
# 2. post_install no Podfile pra propagar pros Pods.xcodeproj
# 3. Adiciona keys obrigatorias no Info.plist (GPS, camera, fotos)
#    Sem isso, o iOS crasha quando o app pede permissao em runtime.
#
# Uso (do diretorio apps/tecnico-mobile):
#   bash scripts/setup-ios.sh
#   cd ios && pod install && cd ..
#   flutter run -d <device>

set -euo pipefail
cd "$(dirname "$0")/.."

PODFILE="ios/Podfile"
PLIST="ios/Runner/Info.plist"

if [ ! -f "$PODFILE" ]; then
  echo "✗ $PODFILE não existe. Roda 'flutter create . --platforms=ios' primeiro."
  exit 1
fi

# ─── 1) Podfile: platform target ───
if grep -qE "^# platform :ios" "$PODFILE"; then
  sed -i.bak "s/^# platform :ios.*/platform :ios, '13.0'/" "$PODFILE"
  echo "✓ Descomentei platform :ios e setei 13.0"
elif grep -qE "^platform :ios" "$PODFILE"; then
  sed -i.bak "s/^platform :ios.*/platform :ios, '13.0'/" "$PODFILE"
  echo "✓ Atualizei platform :ios pra 13.0"
fi

# ─── 2) Podfile: post_install pros pods ───
if ! grep -q "IPHONEOS_DEPLOYMENT_TARGET = '13.0'" "$PODFILE"; then
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

# ─── 3) Info.plist: permissoes obrigatorias ───
if [ ! -f "$PLIST" ]; then
  echo "⚠ $PLIST não existe — pulando patches de permissao"
else
  python3 <<'PY'
import pathlib, re
path = pathlib.Path('ios/Runner/Info.plist')
src = path.read_text()

# Keys obrigatorias e suas mensagens (mostradas no prompt de permissao do iOS).
keys = {
    'NSLocationWhenInUseUsageDescription':
        'BlaBla usa sua localização pra marcar o GPS quando você inicia ou conclui uma OS.',
    'NSCameraUsageDescription':
        'BlaBla precisa da câmera pra você anexar fotos da visita à OS.',
    'NSPhotoLibraryUsageDescription':
        'BlaBla precisa acessar suas fotos pra você anexar imagens à OS ou ao perfil.',
    'NSPhotoLibraryAddUsageDescription':
        'BlaBla pode salvar fotos da OS no seu rolo de câmera.',
    'NSFaceIDUsageDescription':
        'BlaBla usa o Face ID pra te identificar rapidamente ao reabrir o app.',
}

added = []
for key, value in keys.items():
    if f"<key>{key}</key>" in src:
        continue
    inject = f"\t<key>{key}</key>\n\t<string>{value}</string>\n"
    src = re.sub(r"</dict>\s*</plist>\s*$", inject + "</dict>\n</plist>\n", src)
    added.append(key)

if added:
    path.write_text(src)
    print(f"✓ Info.plist: adicionei {len(added)} keys ({', '.join(added)})")
else:
    print("✓ Info.plist: todas as keys ja presentes")
PY
fi

echo ""
echo "✓ Setup iOS OK. Proximos passos:"
echo "    cd ios && pod install && cd .."
echo "    flutter run -d <device>"
