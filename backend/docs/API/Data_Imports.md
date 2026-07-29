# Managed Data Imports

The import workflow supports employee data from HR and schedules from shift managers.
CSV and XLSX files use a preview-first workflow so a file never changes operational
data before an authorized user confirms it.

## Lifecycle

1. Upload a file to a preview endpoint.
2. Review valid row counts and persisted row errors.
3. Confirm or reject the pending job.
4. Roll back a completed job if the imported result must be reverted.

Possible statuses are `PENDING`, `COMPLETED`, `PARTIAL`, `REJECTED`, `FAILED`, and
`ROLLED_BACK`.

## Employee import

Authorized roles: `HR`, `ADMIN`.

Required columns:

```text
employee_code,first_name,last_name,mobile,department,role
```

Optional columns:

```text
supervisor_code,national_id,employment_status
```

Preview:

```bash
curl -X POST http://127.0.0.1:8000/imports/employees/preview \
  -H "X-User-Id: 1" \
  -F "file=@employees.csv"
```

## Shift import

Authorized roles: `SUPERVISOR`, `ADMIN`.

Required columns:

```text
employee_code,shift_date,shift_name,shift_code,start_time,end_time
```

Dates use `YYYY-MM-DD`; times use `HH:MM`.

## Review endpoints

```text
GET  /imports
GET  /imports/{job_id}
GET  /imports/{job_id}/errors
GET  /imports/{job_id}/records
POST /imports/{job_id}/confirm
POST /imports/{job_id}/reject
POST /imports/{job_id}/rollback
GET  /imports/templates/employees
GET  /imports/templates/shifts
```

## Command-line use

Preview only:

```bash
python tools/import_data.py employees.csv --type employees --user-id 1
```

Preview and confirm:

```bash
python tools/import_data.py shifts.xlsx --type shifts --user-id 2 --confirm
```

`X-User-Id` remains the MVP authentication mechanism. Production-grade identity
authentication is still required before exposing administrative endpoints broadly.
