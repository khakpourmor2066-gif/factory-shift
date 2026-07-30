# Changelog

## 2026-07-29

- Added managed CSV/XLSX imports for HR employees and shift schedules.
- Added preview, persisted row errors, confirm, reject, and snapshot-based rollback.
- Added import authorization, audit records, sample templates, and a CLI helper.
- Added liveness, database readiness, request IDs, structured request logs, and base metrics.
- Protected shift-management endpoints with role checks.
- Added hashed, expiring, revocable user API tokens with audit logging.
- Added a Persian browser UI for HR and shift-manager imports.
- Replaced the production bot smoke message to a fake chat with safe `getMe` and
  `getWebhookInfo` runtime checks.
- Converted generic messaging-provider delivery failures from unhandled 500
  responses to controlled 502 responses.
- Added repeatable production code/database backup and isolated PostgreSQL
  restore-verification tools.
- Upgraded FastAPI, Starlette, and python-multipart to remove known dependency
  vulnerabilities and added dependency auditing to CI.
- Fixed two-step Bale activation so a manually typed mobile number, including
  Persian or Arabic digits, is accepted before the personnel code.

## 2026-07-28

- Added admin dashboard, webhook logs, and audit logging.
- Added contact-sharing activation flow for Bale.
- Added GitHub repo workflow, templates, and release checklist.
- Added branch protection on `main` and CI workflow for backend tests.
- Added a production smoke test script for health, dashboard, and bot webhook verification.

## Notes

This changelog is intentionally lightweight. It tracks release-level milestones rather than every internal commit.
