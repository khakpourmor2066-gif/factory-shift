# API Authentication

Administrative API routes accept a user-scoped bearer token:

```text
Authorization: Bearer <token>
```

Only the SHA-256 hash is stored. The raw token is returned once when it is created.
Tokens can expire and can be revoked by their owner.

## Bootstrap

Before disabling the MVP header, create a token for an existing active operator:

```bash
python tools/bootstrap_api_token.py --user-id 1 --expires-days 30
```

Store the displayed token in the operator's secret manager. Then set:

```text
ALLOW_LEGACY_USER_HEADER=false
```

The old `X-User-Id` header remains available only when
`ALLOW_LEGACY_USER_HEADER=true`. Production should keep it disabled.

On the server, this can be automated without printing the token:

```bash
bash backend/tools/enable_production_bearer_auth.sh 1
```

The operator token is written with root-only permissions to
`/root/.factory_shift_operator_token`.

## Token API

```text
POST   /auth/tokens
GET    /auth/tokens
DELETE /auth/tokens/{token_id}
```

Token creation and revocation are written to the audit log.
