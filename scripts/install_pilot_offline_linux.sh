#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ARCHIVE="$SCRIPT_DIR/TLAMATINI-full-linux-x86_64.tar.gz"
WORK_DIR="$SCRIPT_DIR/tlamatini_full"

if [ ! -f "$ARCHIVE" ]; then
  echo "No encontre el paquete: $ARCHIVE"
  exit 1
fi

echo "Preparando instalacion de TLAMATINI..."
rm -rf "$WORK_DIR"
tar -xzf "$ARCHIVE" -C "$SCRIPT_DIR"

if [ ! -x "$WORK_DIR/install.sh" ]; then
  chmod +x "$WORK_DIR/install.sh"
fi

echo "Instalando TLAMATINI..."
cd "$WORK_DIR"
sh ./install.sh

echo
echo "Instalacion completada."
echo "Si tu sistema no muestra el acceso directo de inmediato, cierra sesion y vuelve a entrar."
