#!/usr/bin/env bash
set -euo pipefail

user_id="${1:-1}"
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
env_file="${project_root}/.env.prod"
compose_file="${project_root}/docker-compose.prod.yml"
token_file="/root/.factory_shift_operator_token"

if [[ ! -f "${env_file}" ]]; then
  echo "production env file not found" >&2
  exit 1
fi

token_result="$(
  cd "${project_root}"
  docker compose -f "${compose_file}" --env-file "${env_file}" exec -T backend \
    python tools/bootstrap_api_token.py --user-id "${user_id}" --name production-operator --expires-days 90
)"
raw_token="$(
  python3 -c 'import json,sys; result=json.load(sys.stdin); assert result["status"]=="created"; print(result["token"])' \
    <<<"${token_result}"
)"

umask 077
printf '%s\n' "${raw_token}" > "${token_file}"

python3 - "${env_file}" <<'PY'
import os
import sys
import tempfile
from pathlib import Path

env_path = Path(sys.argv[1])
lines = env_path.read_text(encoding="utf-8").splitlines()
output = []
updated = False
for line in lines:
    if line.startswith("ALLOW_LEGACY_USER_HEADER="):
        output.append("ALLOW_LEGACY_USER_HEADER=false")
        updated = True
    else:
        output.append(line)
if not updated:
    output.append("ALLOW_LEGACY_USER_HEADER=false")

file_descriptor, temporary_name = tempfile.mkstemp(dir=env_path.parent)
try:
    with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as file:
        file.write("\n".join(output) + "\n")
    os.chmod(temporary_name, 0o600)
    os.replace(temporary_name, env_path)
finally:
    if os.path.exists(temporary_name):
        os.unlink(temporary_name)
PY

cd "${project_root}"
docker compose -f "${compose_file}" --env-file "${env_file}" up -d --no-deps --force-recreate backend >/dev/null
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

legacy_status="$(
  curl -sS -o /dev/null -w "%{http_code}" \
    -H "X-User-Id: ${user_id}" \
    http://127.0.0.1:8000/auth/tokens
)"
bearer_status="$(
  curl -sS -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${raw_token}" \
    http://127.0.0.1:8000/auth/tokens
)"

test "${legacy_status}" = "401"
test "${bearer_status}" = "200"
echo "legacy_header_status=${legacy_status}"
echo "bearer_status=${bearer_status}"
echo "token_file=${token_file}"
