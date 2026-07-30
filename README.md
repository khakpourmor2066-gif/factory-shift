# Factory Shift

Factory Shift is a FastAPI-based MVP for factory shift management and Bale messenger integration. It covers employee schedules, supervisor views, access requests, webhook observability, HR identity activation, and a lightweight operations dashboard.

## Features

- Employee and supervisor shift views
- Bale bot webhook handling
- Access request review flow
- HR contact plus personnel-code activation
- Webhook logs and audit logs
- Admin dashboard for operational status
- Managed schedule generation with preview, draft confirmation, cancellation,
  and publication from Bale or the Persian web form
- Seeded demo scenarios for repeatable testing

## Tech Stack

- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL
- Docker Compose
- Nginx
- Bale messenger integration

## Repository Layout

- `backend/` application code, tests, tools, and backend docs
- `docker-compose.yml` local development stack
- `docker-compose.prod.yml` production runtime stack
- `.github/workflows/` CI/CD automation

## Documentation

- [Development workflow](backend/docs/Development_Workflow.md)
- [Release checklist](backend/docs/Release_Checklist.md)
- [Release process](backend/docs/Release_Process.md)
- [Changelog](backend/docs/Changelog.md)
- [Contributing guide](CONTRIBUTING.md)

## Local Development

1. Install dependencies from `backend/requirements.txt`.
2. Run the backend with the local compose stack.
3. Execute the pytest suite before committing.

## Production Notes

- Production uses Docker Compose on the server.
- The public webhook endpoint is routed through Nginx and HTTPS.
- Runtime secrets are stored in `.env.prod` on the server, not in Git.

## Testing

Run the backend test suite from `backend/`:

```bash
python -m pytest -q
```

## Current Status

- Main branch is tracked on GitHub.
- The server is treated as disposable runtime state.
- GitHub is the source of truth for code and documentation.
- CI protects `main` through the `test` check.
- Production database migrations are at `0011_schedule_generation`.
- The HR/Admin schedule-generation form is available at
  `/admin/schedule-generator`.

## Future Work

- Hardening the deployment pipeline
- Adding more branch protections and PR checks
- Expanding operational dashboards and workflow automation
