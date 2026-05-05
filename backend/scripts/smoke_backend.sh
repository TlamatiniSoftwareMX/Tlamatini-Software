#!/usr/bin/env sh
set -eu

BASE_URL="${1:-http://127.0.0.1:8000}"

echo "Probando $BASE_URL/health"
curl -fsS "$BASE_URL/health"
echo
echo "Probando $BASE_URL/version"
curl -fsS "$BASE_URL/version"
echo
echo "Backend OK"
