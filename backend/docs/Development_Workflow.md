# Development Workflow

## Branching

- `main` is the stable branch.
- Use short-lived `feature/*` branches for new work.
- Merge into `main` only after local tests pass.
- Delete feature branches after merge.

## Commit format

Use small, focused commits with this pattern:

```text
type(scope): short imperative summary
```

Examples:

- `feat(bot): add operations menu`
- `fix(seed): avoid duplicate demo requests`
- `chore(deploy): update prod compose`

## Local flow

1. Make the change locally.
2. Create a `feature/*` branch for the task.
3. Run the relevant tests.
4. Commit only the related files.
5. Push the feature branch.
6. Merge to `main` after review and verification.

## Server flow

1. Sync only the runtime files that changed.
2. Rebuild the backend container if app code changed.
3. Rerun the minimal smoke tests.
4. Keep `docker compose --env-file .env.prod` for production commands.

## Notes

- Keep secrets out of git.
- Treat server state as disposable; source of truth is GitHub.
- Use `main` as the recovery point if the server is deleted or recreated.
- Keep server deploys tied to a known commit SHA.
