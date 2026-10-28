# shared-auth

The access-token contract shared by the auth service (issuer) and the main app (consumer), plus
roles, deterministic IDs and optional DRF classes. No Django project, settings or database
needed; tests run standalone.

Import name `shared_auth`; install `shared-auth`, or `shared-auth[drf]` for the DRF classes.

## Modules and who uses them

| Module | Auth service (issuer) | Main app (consumer) |
|---|---|---|
| `shared_auth.tokens`: `issue`, `public_jwk` | signs access tokens, publishes its JWKS | – |
| `shared_auth.tokens`: `verify`, `Claims` | tests | via `shared_auth.drf` |
| `shared_auth.roles`: `Role` | stores and issues roles | via `IsEditor` |
| `shared_auth.drf`: `JWTAuthentication`, `IsEditor` | – | subclass `JWTAuthentication` and set `key_source` (an object with `get()` and `refresh()`, e.g. a cached JWKS fetch) |
| `shared_auth.ids`: `deterministic_uuid` | wp_users import | reviewer link to auth user |

`verify` requires `exp`, `sub` and `role`, and a `version` in `ACCEPTED_VERSIONS`. A token signed
by an unknown kid makes `JWTAuthentication` call `key_source.refresh()` once and try again.

## Tests

```bash
python -m venv .venv && .venv/bin/pip install -e '.[test]' && .venv/bin/pytest
```

## Claims version compatibility

Tokens carry a `version` claim. `tokens.py` sets `ISSUED_VERSION` (what `issue` signs) and
`ACCEPTED_VERSIONS` (what `verify` takes; anything else raises `UnsupportedVersion`). A breaking
claims change is released expand-then-contract, one edit per release:

1. **Expand**: add the new version to `ACCEPTED_VERSIONS`. Deploy it to the main app (consumer) first, then confirm.
2. **Switch**: set `ISSUED_VERSION` to the new version. Deploy the auth service (issuer); existing tokens still verify (access tokens live 10 minutes).
3. **Contract**: once all old tokens have expired, remove the old version from `ACCEPTED_VERSIONS`; consumers update at their leisure.

Never deploy the issuer before every consumer accepts the new version.
