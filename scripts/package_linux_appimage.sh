#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."

if [ ! -f dist/tlamatini_full/TLAMATINI ]; then
  echo "Falta dist/tlamatini_full/TLAMATINI"
  exit 1
fi

if ! command -v appimagetool >/dev/null 2>&1; then
  echo "Falta appimagetool en el sistema."
  exit 1
fi

rm -rf AppDir
mkdir -p AppDir
cp dist/tlamatini_full/TLAMATINI AppDir/TLAMATINI
cp installer/linux/TLAMATINI.desktop AppDir/TLAMATINI.desktop
cp assets/app_icon.png AppDir/tlamatini.png
cp installer/linux/AppRun AppDir/AppRun
chmod +x AppDir/AppRun AppDir/TLAMATINI

appimagetool AppDir dist/TLAMATINI-full-linux-x86_64.AppImage
echo "AppImage generado en dist/TLAMATINI-full-linux-x86_64.AppImage"
