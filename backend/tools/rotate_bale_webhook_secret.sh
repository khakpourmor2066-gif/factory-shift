#!/usr/bin/env bash
set -euo pipefail

public_base_url="${1:?usage: rotate_bale_webhook_secret.sh https://public.example.com}"
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
env_file="${project_root}/.env.prod"
compose_file="${project_root}/docker-compose.prod.yml"

if [[ ! -f "${env_file}" ]]; then
  echo "production env file not found" >&2
  exit 1
fi

new_secret="$(openssl rand -hex 32)"

python3 - "${env_file}" "${new_secret}" "${public_base_url%/}" <<'PY'
import os
import sys
import tempfile
from pathlib import Path

env_path = Path(sys.argv[1])
secret = sys.argv[2]
public_base_url = sys.argv[3]
updates = {
    "BOT_WEBHOOK_SECRET": secret,
    "BALE_WEBHOOK_URL": f"{public_base_url}/bot/bale/webhook/{secret}",
}
lines = env_path.read_text(encoding="utf-8").splitlines()
seen = set()
output = []
for line in lines:
    key = line.split("=", 1)[0] if "=" in line else ""
    if key in updates:
        output.append(f"{key}={updates[key]}")
        seen.add(key)
    else:
        output.append(line)
for key, value in updates.items():
    if key not in seen:
        output.append(f"{key}={value}")

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
docker compose -f "${compose_file}" --env-file "${env_file}" up -d --force-recreate backend >/dev/null

for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
curl -fsS http://127.0.0.1:8000/health >/dev/null

set -a
source "${env_file}"
set +a
docker compose -f "${compose_file}" --env-file "${env_file}" exec -T backend \
  python tools/configure_bale_webhook.py set --url "${BALE_WEBHOOK_URL}" >/dev/null

webhook_result="$(
  docker compose -f "${compose_file}" --env-file "${env_file}" exec -T backend \
    python tools/configure_bale_webhook.py get
)"
python3 -c \
  'import json,sys; result=json.load(sys.stdin); assert result["ok"]; print("bale_webhook_ok=true"); print(f"pending_update_count={result.get(\"result\",{}).get(\"pending_update_count\",0)}")' \
  <<<"${webhook_result}"

echo "webhook_secret_rotated=true"
