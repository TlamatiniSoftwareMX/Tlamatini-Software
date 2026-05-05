#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
PYTHONUNBUFFERED=1 exec python3 scripts/local_ai_tool.py verify_local_ai
