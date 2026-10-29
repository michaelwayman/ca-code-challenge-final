# cauth

Small shared library: the access-token claims (`Claims`, `Role`), JWT verification and DRF auth classes.
No Django project, settings or database needed; tests run standalone.

## Modules and who imports them

| Module | Auth service (S2) | Main app (S1) |
|---|---|---|
| `cauth.tokens.Claims`, `Role` | builds the claims it issues (`Claims.to_payload`), stores roles | via `verify` and `IsEditor` |
| `cauth.tokens.verify`, `CLAIMS_VERSION` | sanity checks / tests | via `cauth.drf` |
| `cauth.drf` (`JWTAuthentication`, `IsEditor`) | – | DRF settings; subclass `JWTAuthentication` and implement `get_jwks()` (cached JWKS fetch) |

## Tests

```bash
python -m venv .venv && .venv/bin/pip install -e '.[test]' && .venv/bin/pytest
```

## Releasing

The version is `__version__` in `src/cauth/__init__.py`; `pyproject.toml` reads it. Any change under `libs/` needs a bump, then update the `cauth==` pin in `services/auth/requirements.txt` and `app/requirements.txt`. See the root README.

## Claims version compatibility

Tokens carry a `version` claim. `verify` accepts the current `CLAIMS_VERSION` (N) and N-1, and
raises `UnsupportedVersion` otherwise. A breaking claims change is released expand-then-contract:

1. **Expand**: release the library at version N+1 that accepts N and N+1. Deploy it to the main app (consumer) first, then confirm.
2. Deploy the auth service (issuer) with the new library; it starts issuing N+1. Existing N tokens still verify (access tokens live 10 minutes).
3. **Contract**: once all N tokens have expired, release the library with `CLAIMS_VERSION` bumped to the new version, which drops the old N-1; consumers update at their leisure.

Never deploy the issuer before every consumer accepts the new version.
