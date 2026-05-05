#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."

if [ ! -f dist/tlamatini_full/TLAMATINI ]; then
  echo "Falta dist/tlamatini_full/TLAMATINI"
  exit 1
fi

ROOT=pkg_deb
VERSION="${TLAMATINI_APP_VERSION:-5.2.2}"
rm -rf "$ROOT"
mkdir -p "$ROOT/DEBIAN" "$ROOT/opt/tlamatini" "$ROOT/usr/share/applications" "$ROOT/usr/share/pixmaps" "$ROOT/usr/bin"
cp dist/tlamatini_full/TLAMATINI "$ROOT/opt/tlamatini/TLAMATINI"
cp installer/linux/TLAMATINI.desktop "$ROOT/usr/share/applications/tlamatini.desktop"
cp assets/app_icon.png "$ROOT/usr/share/pixmaps/tlamatini.png"
chmod 755 "$ROOT/opt/tlamatini/TLAMATINI"

cat > "$ROOT/usr/bin/tlamatini" <<'EOF'
#!/usr/bin/env sh
exec /opt/tlamatini/TLAMATINI "$@"
EOF
chmod 755 "$ROOT/usr/bin/tlamatini"

cat > "$ROOT/DEBIAN/postinst" <<'EOF'
#!/usr/bin/env sh
set -eu

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi
if command -v xdg-desktop-menu >/dev/null 2>&1; then
  xdg-desktop-menu forceupdate >/dev/null 2>&1 || true
fi
EOF
chmod 755 "$ROOT/DEBIAN/postinst"

cat > "$ROOT/DEBIAN/control" <<'EOF'
Package: tlamatini
Version: __TLAMATINI_VERSION__
Section: utils
Priority: optional
Architecture: amd64
Maintainer: TLAMATINI
Description: TLAMATINI Full con IA local embebida
EOF

sed -i "s/__TLAMATINI_VERSION__/$VERSION/" "$ROOT/DEBIAN/control"

DEB_PATH="dist/tlamatini-${VERSION}-amd64.deb"
dpkg-deb --build "$ROOT" "$DEB_PATH"
echo "Paquete DEB generado en $DEB_PATH"
