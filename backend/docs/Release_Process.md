# Release Process

1. Finish the change on a `feature/*` branch.
2. Run the relevant tests locally.
3. Review the diff for secrets, generated files, and unrelated edits.
4. Push the branch to GitHub.
5. Open a pull request into `main`.
6. Wait for the CI check to pass.
7. Merge the pull request.
8. Deploy from the merged commit SHA.
9. Run the server smoke tests.
10. Record the release in the changelog and runbook if needed.

## Deployment Rule

Production deploys should always reference a known Git commit SHA. The server is runtime state only.
