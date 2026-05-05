#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
sh scripts/build_full_release_linux.sh
