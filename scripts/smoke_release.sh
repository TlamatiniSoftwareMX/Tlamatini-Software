#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3 scripts/verify_release_bundle.py dist/tlamatini_full
