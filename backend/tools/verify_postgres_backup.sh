#!/usr/bin/env bash
set -euo pipefail

backup_file="${1:-}"
if [[ -z "${backup_file}" || ! -s "${backup_file}" ]]; then
  echo "a non-empty PostgreSQL .sql.gz backup is required" >&2
  exit 1
fi

container_name="factory_shift_restore_verify_$$"

cleanup() {
  docker rm -f "${container_name}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run -d \
  --name "${container_name}" \
  -e POSTGRES_PASSWORD=restore-verification-only \
  postgres:16 >/dev/null

for _ in $(seq 1 30); do
  if docker exec "${container_name}" pg_isready -U postgres >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

docker exec "${container_name}" pg_isready -U postgres >/dev/null
docker exec "${container_name}" \
  psql -v ON_ERROR_STOP=1 -U postgres -d postgres \
  -c "create role factory_shift login;" >/dev/null

gzip -dc "${backup_file}" |
  docker exec -i "${container_name}" \
    psql -v ON_ERROR_STOP=1 -U postgres -d postgres >/dev/null

counts="$(
  docker exec "${container_name}" \
    psql -U postgres -d postgres -Atc \
    "select (select count(*) from users), (select count(*) from employees), (select count(*) from schedules);"
)"
alembic_revision="$(
  docker exec "${container_name}" \
    psql -U postgres -d postgres -Atc \
    "select version_num from alembic_version;"
)"

printf 'restore_verified=true\n'
printf 'restored_counts=%s\n' "${counts}"
printf 'alembic_revision=%s\n' "${alembic_revision}"
