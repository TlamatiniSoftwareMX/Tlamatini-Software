#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "Falta docker"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Falta docker compose"
  exit 1
fi

POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-tlamatini-smoke-password}"
TLAMATINI_DOMAIN="${TLAMATINI_DOMAIN:-localhost}"
ACME_EMAIL="${ACME_EMAIL:-admin@example.com}"
export POSTGRES_PASSWORD TLAMATINI_DOMAIN ACME_EMAIL

docker compose -f docker-compose.production.yml config >/dev/null
echo "docker compose config OK"

if [ "${TLAMATINI_SMOKE_UP:-0}" = "1" ]; then
  docker compose -f docker-compose.production.yml up -d --build
  echo "Stack levantado. Verifica manualmente /health a través del proxy configurado."
fi
