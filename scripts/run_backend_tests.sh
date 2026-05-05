#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."

PYTHON_BIN="./backend/.venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
  echo "No existe backend/.venv/bin/python"
  exit 1
fi

exec env PYTHONPATH=backend "$PYTHON_BIN" -m pytest backend/tests "$@"
