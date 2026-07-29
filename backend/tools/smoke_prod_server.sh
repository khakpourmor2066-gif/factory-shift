#!/usr/bin/env bash
set -euo pipefail

public_base_url="${1:-https://213.176.6.200.nip.io}"
token_file="${2:-/root/.factory_shift_operator_token}"
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ ! -s "${token_file}" ]]; then
  echo "operator token file not found" >&2
  exit 1
fi

api_token="$(tr -d '\r\n' < "${token_file}")"
cd "${project_root}"
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T backend \
  python tools/smoke_prod.py \
    --base-url "${public_base_url}" \
    --api-token "${api_token}" \
    --skip-bot
