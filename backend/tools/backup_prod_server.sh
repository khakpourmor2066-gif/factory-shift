#!/usr/bin/env bash
set -euo pipefail

release_label="${1:-manual}"
backup_dir="${2:-/opt/backups}"
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ ! "${release_label}" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "release label contains unsupported characters" >&2
  exit 1
fi

cd "${project_root}"
if [[ ! -s .env.prod ]]; then
  echo ".env.prod not found" >&2
  exit 1
fi

timestamp="$(date -u +%Y%m%d_%H%M%S)"
code_backup="${backup_dir}/factory_shift_${release_label}_code_${timestamp}.tar.gz"
database_backup="${backup_dir}/factory_shift_${release_label}_db_${timestamp}.sql.gz"

mkdir -p "${backup_dir}"
tar \
  --exclude='.env.prod' \
  --exclude='.git' \
  -czf "${code_backup}" \
  -C "${project_root}" .

docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T postgres \
  pg_dump -U factory_shift factory_shift_db |
  gzip > "${database_backup}"

chmod 600 "${code_backup}" "${database_backup}"
tar -tzf "${code_backup}" >/dev/null
gzip -t "${database_backup}"

printf 'code_backup=%s\n' "${code_backup}"
printf 'database_backup=%s\n' "${database_backup}"
printf 'backup_verified=true\n'
