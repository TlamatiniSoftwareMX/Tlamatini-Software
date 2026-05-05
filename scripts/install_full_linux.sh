#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SOURCE_BIN="$SCRIPT_DIR/TLAMATINI"
INSTALL_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/TLAMATINI"
BIN_DIR="$INSTALL_ROOT/bin"
APP_BIN="$BIN_DIR/TLAMATINI"
APP_ICON="$INSTALL_ROOT/tlamatini.png"
LOCAL_BIN_DIR="${HOME}/.local/bin"
WRAPPER_BIN="$LOCAL_BIN_DIR/tlamatini"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$DESKTOP_DIR/tlamatini.desktop"
DESKTOP_TARGET_DIR=""
DESKTOP_SHORTCUT=""

resolve_desktop_dir() {
  if [ -n "${XDG_DESKTOP_DIR:-}" ]; then
    printf '%s\n' "$XDG_DESKTOP_DIR"
    return 0
  fi
  USER_DIRS_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/user-dirs.dirs"
  if [ -f "$USER_DIRS_FILE" ]; then
    value=$(grep '^XDG_DESKTOP_DIR=' "$USER_DIRS_FILE" | head -n 1 | cut -d= -f2- | tr -d '"') || true
    if [ -n "${value:-}" ]; then
      value=$(printf '%s' "$value" | sed "s|\$HOME|$HOME|g")
      printf '%s\n' "$value"
      return 0
    fi
  fi
  printf '%s\n' "$HOME/Desktop"
}

if [ ! -f "$SOURCE_BIN" ]; then
  echo "No encontre el bundle Full en: $SOURCE_BIN"
  exit 1
fi

mkdir -p "$BIN_DIR" "$DESKTOP_DIR" "$LOCAL_BIN_DIR"
cp "$SOURCE_BIN" "$APP_BIN"
chmod +x "$APP_BIN"
if [ -f "$SCRIPT_DIR/tlamatini.png" ]; then
  cp "$SCRIPT_DIR/tlamatini.png" "$APP_ICON"
elif [ -f "$SCRIPT_DIR/app_icon.png" ]; then
  cp "$SCRIPT_DIR/app_icon.png" "$APP_ICON"
fi

cat >"$WRAPPER_BIN" <<EOF
#!/usr/bin/env sh
exec "$APP_BIN" "\$@"
EOF
chmod +x "$WRAPPER_BIN"

cat >"$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=TLAMATINI
Comment=TLAMATINI con IA local offline
Exec=$WRAPPER_BIN
Icon=$APP_ICON
Terminal=false
Categories=Utility;
StartupNotify=true
EOF
chmod +x "$DESKTOP_FILE"

DESKTOP_TARGET_DIR=$(resolve_desktop_dir)
if [ -n "$DESKTOP_TARGET_DIR" ]; then
  mkdir -p "$DESKTOP_TARGET_DIR"
  DESKTOP_SHORTCUT="$DESKTOP_TARGET_DIR/TLAMATINI.desktop"
  cp "$DESKTOP_FILE" "$DESKTOP_SHORTCUT"
  chmod +x "$DESKTOP_SHORTCUT"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi
if command -v xdg-desktop-menu >/dev/null 2>&1; then
  xdg-desktop-menu forceupdate >/dev/null 2>&1 || true
fi

echo "TLAMATINI Full instalado en: $APP_BIN"
echo "Acceso directo creado en: $DESKTOP_FILE"
if [ -n "$DESKTOP_SHORTCUT" ]; then
  echo "Acceso directo adicional en escritorio: $DESKTOP_SHORTCUT"
fi
echo "Tambien puedes abrir TLAMATINI ejecutando: $WRAPPER_BIN"
