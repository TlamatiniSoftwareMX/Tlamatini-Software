#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

run_with_python() {
  candidate="$1"
  if [ -z "$candidate" ]; then
    return 1
  fi
  if ! command -v "$candidate" >/dev/null 2>&1 && [ ! -x "$candidate" ]; then
    return 1
  fi
  if "$candidate" -c "import cryptography" >/dev/null 2>&1; then
    exec "$candidate" "$SCRIPT_DIR/generador_licencias_gui.py"
  fi
  return 1
}

run_with_python "$PROJECT_ROOT/.venv/bin/python" || true
run_with_python python3 || true

echo "No se encontró un intérprete válido con cryptography."
echo "Instala dependencias en .venv o usa: python3 -m pip install cryptography"
exit 1
