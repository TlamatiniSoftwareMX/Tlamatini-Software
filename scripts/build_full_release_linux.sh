#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
TLAMATINI_SKIP_RUNTIME_VERIFY="${TLAMATINI_SKIP_RUNTIME_VERIFY:-0}" python3 scripts/local_ai_tool.py build_full_release
python3 scripts/local_ai_tool.py package_full_release
