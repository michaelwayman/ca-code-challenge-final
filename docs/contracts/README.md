# Service contracts

Each contract has one owner and a version. The owner bumps the version when the shape changes; the tests below fail when the code and the contract drift apart.

| Contract | Owner | Version | Checked by |
|---|---|---|---|
| [`token-claims.schema.json`](auth/token-claims.schema.json) | auth service | 1.0.0 | `services/auth/accounts/test_contracts.py`: claims from the real issuer pass through `cauth.verify` and validate against the schema; the schema's `version` values equal `cauth.SUPPORTED_VERSIONS` |
| [`brands-api.openapi.json`](app/brands-api.openapi.json) | main app | 1.0.0 | `services/app/catalog/test_contracts.py`: `/api/brands/` and PATCH responses and the frontend fixture (`frontend/src/fixtures/brands-page.json`) validate against it; page size and orderings in `api.py` and `url.js` agree |

**Version semantics.** Contract versions are semver: a patch is a clarification, a minor adds an optional field, a major removes or changes one. The `version` claim inside a token is separate: it is the claims version N that `cauth` accepts together with N-1, and a breaking claims change is released expand-then-contract (see `libs/cauth/README.md`).

Run the checks with `make contract-test`.

**WP user ids.** Not a schema file: the auth user pk and the reviewer pk are both `uuid5(NAMESPACE_URL, "brand-reviews:wp_user:<wp_user_id>")`. Each service defines it in its `wp_import.py` and pins the same example values in its tests, so a change in one service fails there.
