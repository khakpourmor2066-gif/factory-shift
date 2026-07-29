# Release Checklist

Use this checklist before publishing a new backend or server release.

## Code

- [ ] Review `git diff`
- [ ] Confirm the commit message is specific
- [ ] Verify no secrets or `.env` files are staged
- [ ] Run the relevant test subset
- [ ] Run the full backend test suite when the change is broad

## Repo

- [ ] Push the branch to GitHub
- [ ] Open or update the pull request
- [ ] Confirm `main` only receives reviewed changes
- [ ] Keep branch names short and descriptive

## Server

- [ ] Sync only the files that changed
- [ ] Rebuild the backend container if application code changed
- [ ] Apply the production env file with `docker compose --env-file .env.prod`
- [ ] Run the minimal smoke test after deploy: `python tools/smoke_prod.py --base-url https://your-domain.example`
- [ ] Confirm `/health` is `ok`
- [ ] Confirm `/health/ready` reports database `ok`
- [ ] Confirm migration `0008_data_imports` is applied
- [ ] Confirm `MAX_IMPORT_BYTES` matches the operational limit
- [ ] Bootstrap and store an operator bearer token
- [ ] Set `ALLOW_LEGACY_USER_HEADER=false`
- [ ] Run `smoke_prod.py` with `--api-token`

## Webhook

- [ ] Verify `BALE_WEBHOOK_URL`
- [ ] Confirm webhook registration on Bale
- [ ] Test `/start`
- [ ] Test one approval or contact-activation path

## Recovery

- [ ] Keep the latest commit SHA recorded
- [ ] Confirm the runbook still matches the server layout
- [ ] Verify rollback is possible from GitHub state
- [ ] Preview a sample import and reject it without changing product data
- [ ] Review `docs/Incident_Checklist.md`
