#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3 scripts/local_ai_tool.py run_local_ai
