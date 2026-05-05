#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DB_PATH="${BACKEND_DIR}/tlamatini.db"

if [[ -f "${DB_PATH}" ]]; then
  rm -f "${DB_PATH}"
  echo "SQLite local eliminada: ${DB_PATH}"
else
  echo "No existia base local: ${DB_PATH}"
fi

echo "La siguiente ejecucion del backend recreara el esquema automaticamente."
