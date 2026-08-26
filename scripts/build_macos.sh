#!/usr/bin/env bash
# Construit Reelicious.app (macOS uniquement) : à lancer depuis un
# Terminal dans lequel l'environnement virtuel du projet est déjà activé
# (voir le guide d'installation). Résultat : dist/Reelicious.app.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Installation des outils de build..."
pip install -q -e ".[build]"

echo "Génération de l'icône..."
python scripts/generate_icon.py

echo "Conversion de l'icône en .icns..."
ICONSET="assets/icon.iconset"
rm -rf "$ICONSET"
mkdir "$ICONSET"
sips -z 16 16 assets/icon.png --out "$ICONSET/icon_16x16.png" >/dev/null
sips -z 32 32 assets/icon.png --out "$ICONSET/icon_16x16@2x.png" >/dev/null
sips -z 32 32 assets/icon.png --out "$ICONSET/icon_32x32.png" >/dev/null
sips -z 64 64 assets/icon.png --out "$ICONSET/icon_32x32@2x.png" >/dev/null
sips -z 128 128 assets/icon.png --out "$ICONSET/icon_128x128.png" >/dev/null
sips -z 256 256 assets/icon.png --out "$ICONSET/icon_128x128@2x.png" >/dev/null
sips -z 256 256 assets/icon.png --out "$ICONSET/icon_256x256.png" >/dev/null
sips -z 512 512 assets/icon.png --out "$ICONSET/icon_256x256@2x.png" >/dev/null
sips -z 512 512 assets/icon.png --out "$ICONSET/icon_512x512.png" >/dev/null
cp assets/icon.png "$ICONSET/icon_512x512@2x.png"
iconutil -c icns "$ICONSET" -o assets/icon.icns
rm -rf "$ICONSET"

echo "Nettoyage des anciennes constructions (évite de garder un .app périmé)..."
rm -rf build dist

echo "Empaquetage avec PyInstaller (ça prend quelques minutes)..."
pyinstaller --name Reelicious --windowed --noconfirm \
  --icon assets/icon.icns \
  --add-data "assets:assets" \
  --collect-all faster_whisper \
  --collect-all ctranslate2 \
  --collect-all yt_dlp \
  --collect-all PySide6.QtMultimedia \
  --collect-all PySide6.QtMultimediaWidgets \
  desktop/app.py

echo
echo "Terminé : dist/Reelicious.app"
echo "Glissez-le dans votre dossier Applications pour l'avoir dans le Launchpad / Dock."
