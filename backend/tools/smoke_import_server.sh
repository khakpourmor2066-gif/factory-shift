#!/usr/bin/env bash
set -euo pipefail

public_base_url="${1:-https://213.176.6.200.nip.io}"
token_file="${2:-/root/.factory_shift_operator_token}"
employee_code="${3:-EMP-001}"

if [[ ! -s "${token_file}" ]]; then
  echo "operator token file not found" >&2
  exit 1
fi

api_token="$(tr -d '\r\n' < "${token_file}")"
temporary_directory="$(mktemp -d)"
case "${temporary_directory}" in
  /tmp/tmp.*) ;;
  *) echo "unexpected temporary directory" >&2; exit 1 ;;
esac
trap 'rm -rf -- "${temporary_directory}"' EXIT

cat > "${temporary_directory}/shifts.csv" <<CSV
employee_code,shift_date,shift_name,shift_code,start_time,end_time,source
${employee_code},2099-12-30,Server Smoke,SMOKE,09:00,17:00,SERVER_SMOKE
CSV

curl -fsS \
  -H "Authorization: Bearer ${api_token}" \
  -F "file=@${temporary_directory}/shifts.csv" \
  "${public_base_url%/}/imports/shifts/preview" \
  > "${temporary_directory}/preview.json"

job_id="$(
  python3 -c 'import json,sys; result=json.load(sys.stdin); assert result["job"]["valid_rows"]==1; print(result["job"]["id"])' \
    < "${temporary_directory}/preview.json"
)"

curl -fsS \
  -X POST \
  -H "Authorization: Bearer ${api_token}" \
  "${public_base_url%/}/imports/${job_id}/confirm" \
  > "${temporary_directory}/confirm.json"
python3 -c 'import json,sys; result=json.load(sys.stdin); assert result["status"]=="COMPLETED"' \
  < "${temporary_directory}/confirm.json"

curl -fsS \
  -X POST \
  -H "Authorization: Bearer ${api_token}" \
  "${public_base_url%/}/imports/${job_id}/rollback" \
  > "${temporary_directory}/rollback.json"
python3 -c 'import json,sys; result=json.load(sys.stdin); assert result["status"]=="ROLLED_BACK"' \
  < "${temporary_directory}/rollback.json"

echo "import_smoke_job_id=${job_id}"
echo "preview_status=PENDING"
echo "confirm_status=COMPLETED"
echo "rollback_status=ROLLED_BACK"
