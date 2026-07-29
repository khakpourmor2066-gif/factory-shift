# Incident Checklist

Use this checklist when the API, database, Bale webhook, or import workflow is unhealthy.

## Contain

- Record the incident start time and affected user flow.
- Stop repeated deploys or imports until the failure mode is understood.
- Preserve application, Nginx, PostgreSQL, webhook, and import job logs.
- Revoke a suspected API token without deleting its audit history.

## Diagnose

- Check `GET /health/live` and `GET /health/ready`.
- Check Docker container state and restart count.
- Check the current Alembic revision.
- Check recent `webhook_logs`, `import_jobs`, `import_errors`, and `audit_logs`.
- Confirm disk, memory, database connections, DNS, and certificate validity.
- Confirm Bale webhook registration and the public HTTPS endpoint.

## Recover

- Roll back a bad import through `POST /imports/{job_id}/rollback`.
- Roll back application code to the last reviewed Git commit.
- Apply migrations only after the database backup state is known.
- Rebuild the backend container and run the production smoke test.
- Keep `ALLOW_LEGACY_USER_HEADER=false` unless a controlled bootstrap is required.

## Verify

- Liveness and readiness return 200.
- Bearer authentication succeeds and revoked tokens return 401.
- `tools/check_bale_runtime.py` confirms Bot API access and webhook registration.
- Use a real controlled Bale test account for an end-user `/start` check; never
  send production smoke messages to a fabricated chat ID.
- A preview-only sample import reports expected counts.
- No unexpected schedule or employee rows remain from verification.

## Close

- Document root cause, impact, recovery, and prevention.
- Add or update a regression test.
- Update the changelog if product behavior changed.
- Rotate any credential that may have been exposed.

Rotate the Bale webhook secret without printing its value:

```bash
bash backend/tools/rotate_bale_webhook_secret.sh https://your-domain.example
```
