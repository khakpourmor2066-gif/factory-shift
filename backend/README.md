# Factory Shift Backend

Backend MVP for the Factory Shift Management System.

## Current Scope

Implemented modules:
- Users
- Departments
- Employees
- Shifts
- Employee View
- Supervisor View
- Bot Adapter
- Change Management
- Attendance
- Reports
- Managed employee and shift imports

## Requirements

- Python 3.12+
- PostgreSQL
- FastAPI
- SQLAlchemy
- Alembic
- Pytest

Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment

Create `.env` from `.env.example` and configure:

```text
APP_NAME=Factory Shift
DATABASE_URL=postgresql+psycopg2://factory_shift:factory_shift@localhost:5432/factory_shift_db
SQLALCHEMY_ECHO=false
AUTO_CREATE_TABLES=false
BOT_WEBHOOK_SECRET=local-dev-secret
DEFAULT_BOT_PLATFORM=bale
BALE_BOT_TOKEN=your-bale-bot-token
BALE_API_BASE_URL=https://tapi.bale.ai
BALE_SEND_URL=
RUBIKA_SEND_URL=
MAX_IMPORT_BYTES=5242880
ALLOW_LEGACY_USER_HEADER=true
```

## Database

From the project root, start PostgreSQL:

```bash
docker compose up -d postgres
```

Run migrations from `backend`:

```bash
alembic upgrade head
```

Create repeatable MVP demo data:

```bash
python tools/seed_mvp.py
```

Seeded identifiers:

```text
employee messenger user: emp-1
supervisor messenger user: sup-1
```

Migration chain:
- `0001_initial.py`
- `0002_shift_engine.py`
- `0003_user_access.py`
- `0004_change_management.py`
- `0005_attendance_reports.py`
- `0006_access_requests.py`
- `0007_webhook_logs.py`
- `0008_data_imports.py`

## Run

```bash
uvicorn app.main:app --reload
```

Health check:

```text
GET /health
GET /health/live
GET /health/ready
GET /metrics
```

## Managed Imports

HR employee files and supervisor schedule files support CSV/XLSX preview, persisted
row errors, confirmation, rejection, and rollback.

```bash
python tools/import_data.py employees.csv --type employees --user-id 1
python tools/import_data.py shifts.xlsx --type shifts --user-id 2 --confirm
```

See `docs/API/Data_Imports.md`, `docs/HR_Import_Guide_FA.md`, and
`docs/Shift_Import_Guide_FA.md`.

Browser UI:

```text
GET /admin/imports
```

The page keeps the bearer token only in memory and supports preview, confirm, reject,
rollback, and template download.

## API Authentication

User-scoped bearer tokens are supported. Bootstrap a token for an existing operator,
then disable the legacy `X-User-Id` header in production:

```bash
python tools/bootstrap_api_token.py --user-id 1 --expires-days 30
```

See `docs/API/Authentication.md`.

## Bale Integration

For real Bale delivery:

```text
BALE_BOT_TOKEN=<your token>
BALE_API_BASE_URL=https://tapi.bale.ai
BALE_WEBHOOK_URL=https://your-domain.example/bot/bale/webhook/<secret>
```

The backend sends text messages to:

```text
POST /bot<token>/sendMessage
```

with:

```json
{"chat_id":"<chat id>","text":"<message>"}
```

If `BALE_BOT_TOKEN` is not set, the code can still use the local fallback `BALE_SEND_URL` for simulator mode.

To register the webhook with Bale:

```bash
python tools/configure_bale_webhook.py set --url "https://your-domain.example/bot/bale/webhook/<secret>"
```

To inspect or remove it:

```bash
python tools/configure_bale_webhook.py get
python tools/configure_bale_webhook.py delete
```

## Local Webhook Simulator

Start the API:

```bash
uvicorn app.main:app --reload
```

Simulate an incoming bot webhook:

```bash
python tools/webhook_simulator.py --messenger-user-id emp-1 --text "منو" --secret local-dev-secret
```

Useful examples:

```bash
python tools/webhook_simulator.py --messenger-user-id emp-1 --text "برنامه شیفت من"
python tools/webhook_simulator.py --messenger-user-id sup-1 --text "مشاهده افراد یک روز"
```

The simulator posts to:

```text
POST /bot/webhook
```

It requires:

```text
X-Bot-Secret
```

## E2E MVP Demo

Run a local end-to-end demo with a local sender receiver and the live API:

```bash
python tools/e2e_mvp_demo.py
```

This demo verifies:
- webhook reception
- response generation
- outbound message delivery
- employee and supervisor flows

Custom example:

```bash
python tools/e2e_mvp_demo.py --api-url http://127.0.0.1:8003 --api-port 8003 --receiver-port 9003 --secret local-dev-secret
```

Custom scenarios:

```bash
python tools/e2e_mvp_demo.py --scenario "emp-1|منو" --scenario "sup-1|مشاهده افراد یک روز"
```

Save JSON output:

```bash
python tools/e2e_mvp_demo.py --output e2e_output.json
```

CI-style command:

```bash
python tools/ci_mvp.py --artifact artifacts/e2e_output.json
```

This command runs:
- tests
- migrations
- seed
- end-to-end demo

## Production Smoke Test

After deploy, verify the runtime with:

```bash
python tools/smoke_prod.py --base-url https://your-domain.example --run-seed
```

The smoke test checks:
- `/health`
- `/health/ready`
- admin dashboard access with a seeded supervisor user
- a bot webhook round trip

Sample employee table:
- `backend/docs/Sample_Employees.md`

Seed this sample into the database:

```bash
python tools/seed_sample_employees.py --seed-base
```

If you do not want the script to seed demo data again, omit `--run-seed`.

## Tests

```bash
pytest
```

## MVP Test Scenario

1. Create department.
2. Create user.
3. Create employee.
4. Link user to employee.
5. Create shift pattern.
6. Create assignment.
7. Generate schedule.
8. View employee schedule.
9. View supervisor schedule.

## Important Notes

- `X-User-Id` is a temporary MVP access mechanism.
- Real authentication is not implemented yet.
- Bot adapters for Bale and Rubika are skeletons.
- Attendance import remains row-based; employee and shift imports support CSV/XLSX.
- Production should rely on Alembic migrations.
- `AUTO_CREATE_TABLES` must stay `false` outside local experiments.
