# Contributing

This repository is maintained as a production-grade portfolio project. Keep changes small, reviewable, and safe to deploy.

## Structure

- Keep files in logical folders.
- Avoid ad-hoc root files unless they are required for repository-level setup.
- Use descriptive names for files, folders, functions, and branches.

Avoid vague names like `temp.py`, `final.py`, or `new.py`.

## Documentation

- Keep `README.md` current with purpose, features, setup, usage, architecture, and limitations.
- Add supporting documentation in `backend/docs/` when it improves handoff or recovery.
- Keep runbooks and deployment notes close to the code they describe.

## Commits

- Make each commit represent one meaningful step.
- Use clear messages such as `feat(bot): add operations menu`.
- Avoid generic messages like `update`, `fix`, `change`, or `test`.

## Security

- Never commit real secrets, passwords, tokens, private keys, or live `.env` files.
- Commit `.env.example` files instead of production config.
- Check `git diff` before every push.

## Ignore Rules

- Keep caches, build artifacts, virtual environments, and IDE metadata out of Git.
- Keep `__pycache__`, `*.pyc`, `.pytest_cache`, `venv`, `.idea`, and `.vscode` ignored.

## Testing

- Run the relevant tests before committing.
- Verify the main path of any changed workflow.
- If a change touches deployment or webhook behavior, run a smoke test.

## Branching

- `main` is the stable branch.
- Use `feature/*` branches for active work.
- Merge into `main` only after tests pass.
- Delete feature branches after merge.

## Release Flow

1. Review the diff.
2. Verify security-sensitive files.
3. Run the relevant tests.
4. Commit with a focused message.
5. Push the branch.
6. Deploy from a known commit SHA.

## Project Intent

- Treat GitHub as the source of truth.
- Treat the server as disposable runtime state.
- Preserve a clear path to recovery if the server is recreated or deleted.
