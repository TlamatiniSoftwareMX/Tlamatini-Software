#!/usr/bin/env sh
set -eu

REPOSITORY="TlamatiniSoftwareMX/Tlamatini-Software"
VERSION="5.2.6"
PARTS="44"
EXPECTED_SHA256="85c3c6333064986219c8963774e5eb84e8fd41f495cde4f8a9cf58e01e913177"
RELEASE_BASE_URL="https://github.com/${REPOSITORY}/releases/download/v${VERSION}"
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/tlamatini-install.XXXXXX")
OUTPUT="${WORK_DIR}/tlamatini-${VERSION}-amd64.deb"

cleanup() {
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT HUP INT TERM

if [ "$(uname -m)" != "x86_64" ] && [ "$(uname -m)" != "amd64" ]; then
    echo "Error: este instalador requiere Linux de 64 bits (amd64/x86_64)." >&2
    exit 1
fi

if ! command -v apt >/dev/null 2>&1; then
    echo "Error: este instalador requiere Ubuntu, Debian, Linux Mint o un sistema con apt." >&2
    exit 1
fi

if command -v curl >/dev/null 2>&1; then
    download() {
        curl -fL --retry 4 --retry-delay 2 --connect-timeout 30 -o "$2" "$1"
    }
elif command -v wget >/dev/null 2>&1; then
    download() {
        wget --tries=4 --timeout=30 -O "$2" "$1"
    }
else
    echo "Error: instala curl o wget para descargar TLAMATINI." >&2
    exit 1
fi

echo "Descargando TLAMATINI ${VERSION} desde GitHub (44 partes, aproximadamente 2.7 GB)..."
part=1
while [ "$part" -le "$PARTS" ]; do
    number=$(printf '%03d' "$part")
    name="tlamatini-${VERSION}-linux-amd64.chunk-${number}-of-044"
    echo "[$part/$PARTS] $name"
    download "${RELEASE_BASE_URL}/${name}" "${WORK_DIR}/${name}"
    part=$((part + 1))
done

set -- "${WORK_DIR}"/tlamatini-${VERSION}-linux-amd64.chunk-???-of-044
if [ "$#" -ne "$PARTS" ]; then
    echo "Error: no se descargaron correctamente las 44 partes." >&2
    exit 1
fi

cat "$@" > "$OUTPUT"
ACTUAL_SHA256=$(sha256sum "$OUTPUT" | awk '{print $1}')
if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
    echo "Error: la verificación SHA-256 del instalador no coincide." >&2
    exit 1
fi

echo "Instalador reconstruido y verificado correctamente."
echo "El sistema puede solicitar tu contraseña para instalar TLAMATINI."
sudo apt install -y "$OUTPUT"

echo ""
echo "TLAMATINI ${VERSION} quedó instalado correctamente."
echo "Puedes abrirlo desde el menú de aplicaciones o ejecutando: tlamatini"
