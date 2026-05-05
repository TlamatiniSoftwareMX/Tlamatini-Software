#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
if [ -x ".venv/bin/python" ]; then
  exec ".venv/bin/python" scripts/local_ai_tool.py build_portable
fi
exec python3 scripts/local_ai_tool.py build_portable
