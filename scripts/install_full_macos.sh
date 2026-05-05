#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SOURCE_APP="$SCRIPT_DIR/TLAMATINI.app"
TARGET_APP="/Applications/TLAMATINI.app"

if [ ! -d "$SOURCE_APP" ]; then
  echo "No encontre TLAMATINI.app junto al instalador."
  exit 1
fi

rm -rf "$TARGET_APP"
cp -R "$SOURCE_APP" "$TARGET_APP"

echo "TLAMATINI Full instalado en: $TARGET_APP"
