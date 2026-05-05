#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3 scripts/local_ai_tool.py download_models
