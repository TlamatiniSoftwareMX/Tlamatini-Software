#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."

if [ ! -d dist/tlamatini_full/TLAMATINI.app ]; then
  echo "Falta dist/tlamatini_full/TLAMATINI.app"
  exit 1
fi

if ! command -v hdiutil >/dev/null 2>&1; then
  echo "Falta hdiutil en este sistema."
  exit 1
fi

rm -f dist/TLAMATINI-full-macos.dmg
hdiutil create -volname TLAMATINI -srcfolder dist/tlamatini_full/TLAMATINI.app -ov -format UDZO dist/TLAMATINI-full-macos.dmg
echo "DMG generado en dist/TLAMATINI-full-macos.dmg"
