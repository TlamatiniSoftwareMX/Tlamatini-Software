#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
EMAIL="trial.$(date +%s)@example.com"
PASSWORD="ClaveSegura123"
INSTALLATION_ID="inst-trial-$(date +%s)"

echo "Usando backend: ${BASE_URL}"
echo "Email de prueba: ${EMAIL}"
echo "Installation ID: ${INSTALLATION_ID}"

REGISTER_PAYLOAD=$(cat <<JSON
{"email":"${EMAIL}","password":"${PASSWORD}","preferred_language":"es"}
JSON
)

LOGIN_PAYLOAD=$(cat <<JSON
{"email":"${EMAIL}","password":"${PASSWORD}"}
JSON
)

INSTALL_PAYLOAD=$(cat <<JSON
{"installation_id":"${INSTALLATION_ID}","device_name":"Equipo TLAMATINI","os_name":"Linux","app_version":"0.1.0"}
JSON
)

TRIAL_PAYLOAD=$(cat <<JSON
{"installation_id":"${INSTALLATION_ID}"}
JSON
)

curl -sS -X POST "${BASE_URL}/auth/register" -H "Content-Type: application/json" -d "${REGISTER_PAYLOAD}"
echo

LOGIN_RESPONSE=$(curl -sS -X POST "${BASE_URL}/auth/login" -H "Content-Type: application/json" -d "${LOGIN_PAYLOAD}")
echo "${LOGIN_RESPONSE}"
echo

ACCESS_TOKEN=$(printf '%s' "${LOGIN_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
AUTH_HEADER="Authorization: Bearer ${ACCESS_TOKEN}"

curl -sS -X POST "${BASE_URL}/installations/register" -H "Content-Type: application/json" -H "${AUTH_HEADER}" -d "${INSTALL_PAYLOAD}"
echo

TRIAL_RESPONSE=$(curl -sS -X POST "${BASE_URL}/licenses/trial" -H "Content-Type: application/json" -H "${AUTH_HEADER}" -d "${TRIAL_PAYLOAD}")
echo "${TRIAL_RESPONSE}"
echo

SIGNED_PAYLOAD=$(printf '%s' "${TRIAL_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["signed_payload"])')

curl -sS -G "${BASE_URL}/licenses/status" -H "${AUTH_HEADER}" --data-urlencode "installation_id=${INSTALLATION_ID}"
echo

VERIFY_PAYLOAD=$(cat <<JSON
{"signed_payload":"${SIGNED_PAYLOAD}"}
JSON
)

curl -sS -X POST "${BASE_URL}/licenses/verify" -H "Content-Type: application/json" -d "${VERIFY_PAYLOAD}"
echo
