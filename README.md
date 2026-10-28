# Brand Reviews: WordPress to Django

A small consumer-reviews site (brands, reviews, industries) rebuilt from WordPress as a Django system: a main app with server-rendered pages and a brand-listing API, a React `<BrandList />` component, an SCSS source tree, a separate Django auth service, and a shared Python library. Docker is the only prerequisite.

**This is dev-grade by design.** It's a challenge submission, not a deployable service; see [What production would need](#what-production-would-need).

## Quick start

```bash
cp .env.example .env
make up       # builds and starts WordPress + MariaDB, auth + auth-db, app + app-db, and waits until healthy
make import   # WordPress -> main app, wp_users -> auth users (safe to re-run)
```

The compiled frontend is committed, so nothing else is needed; run `make fe-build` only after changing the SCSS or React code. `make help` lists every target.

**Starting over:** `make reset` wipes every volume (WordPress, both Postgres databases, the signing key), then `make up` and `make import` rebuild from scratch. Remove only the containers and the old volumes survive; an auth database left over from an earlier import can then fail `make import` with a duplicate `admin` username. Use `make reset`, not a manual delete.

| What | URL |
|---|---|
| Main app (home, `/brand/<slug>/`, `/review/<slug>/`, `/brands/`, `/api/brands/`) | <http://localhost:8000> |
| Auth service (`POST /auth/login`, JWKS) | <http://localhost:8001> |
| WordPress source (admin / admin) | <http://localhost:8080> |

The WordPress database is seeded from `db/dump.sql` on first boot, and both imports read it live from MariaDB.

## Run the pieces

### Main app

`make up` starts `app` (Django `runserver`) with its own Postgres. `./frontend` is mounted read-only and served at `/static/`, so a frontend rebuild shows on refresh with no restart.

### Auth service

Its own Django project, container and Postgres. `import_wp_users` creates one user per `wp_users` row (id = `deterministic_uuid('wp_user', ID)`); WP `administrator` and `editor` become `editor`, everything else `reader`. **WP password hashes are carried over verbatim and upgraded to Django's default hasher on the user's first successful login** (see `auth/accounts/hashers.py`). Roles are edited in the Django admin; create an operator with `make operator`. The main app stores no passwords or roles.

### React component and SCSS

`frontend/src/BrandList.jsx` is mounted on `/brands/` by `main.jsx`; Django passes the industry options through `json_script`.

```bash
make fe-build   # npm ci + sass + vite build -> frontend/dist/css/main.css, frontend/dist/js/brand-list.js
make fe-dev     # same, rebuilding on change
make fe-test    # vitest + Testing Library + axe, in Docker
```

The SCSS tree under `frontend/scss/` is compiled with `sass frontend/scss/main.scss` (no warnings). `abstracts/_tokens.scss` is the only place design tokens are defined; `components/` has one partial per component. **To add a component:** create `components/_name.scss` and add `@use "components/name";` to `main.scss`.

## Get a token and call the protected endpoint

`PATCH /api/brands/<slug>/` needs an editor's access token from the auth service. WordPress's `admin` user is an editor; on a fresh import its password is `admin`.

```bash
make token                                        # prints an access token for admin / admin
make patch-brand SLUG=acme-insurance DESC="Fair prices, slow claims."   # logs in, then PATCHes the brand
```

`make token` and `make patch-brand` take `AUTH_USER` and `AUTH_PASS` (default `admin` / `admin`). Underneath they call `POST /auth/login` on the auth service and `PATCH /api/brands/<slug>/` on the main app with the bearer token.

| Request | Response |
|---|---|
| Editor token | 200 with the updated row |
| Reader token | 403 |
| No token, malformed, bad signature, expired, unknown key | 401 (`WWW-Authenticate: Bearer`) |
| Any key besides `short_description`, or none | 400; nothing is written |
| `PUT` | 405 |

**If login says `Invalid credentials`:** the `admin` password only matches on a fresh import. The auth service sets a user's password when it creates the account and never overwrites it afterwards, so an account whose password was changed (or that you reset) keeps the new one. Set it back for local development with:

```bash
make admin-password   # prompts for a new password for AUTH_USER (default admin)
```

Login also returns a refresh token. `POST /auth/refresh` returns a new access token with the user's current role, and `POST /auth/logout` revokes the refresh token.

### When the auth service is down

The main app never calls the auth service per request. It verifies tokens locally with the public keys from `http://auth:8001/.well-known/jwks.json`, cached in process (`app/config/auth.py`), and compose deliberately has no `depends_on: auth` for it.

- **Reads** (`/api/brands/`, `/api/brands/<slug>/`, pages, `/healthz`) never touch auth and keep returning 200.
- **Writes with a still-valid token** keep working: the key set is refetched every 5 minutes, and a failed refetch keeps the last good set. Revocation therefore rests on the 10-minute token lifetime.
- **Cold cache** (main app restarted while auth is down): there is nothing to verify against, so writes fail closed with **503** `Signing keys unavailable`.
- A failed fetch is not retried for 30 seconds, and a token with an unknown `kid` triggers an immediate refetch, at most once per 30 seconds.

Try it: `make auth-stop`, then `make patch-brand` fails at login (auth is down) but `/api/brands/` still returns 200; with a token you already hold, a `PATCH` still succeeds; after `make app-restart` the same `PATCH` returns 503; `make auth-start` restores it.

## Brand listing API

`GET /api/brands/` is public and returns `{count, next, previous, results}`. Each row has `name`, `slug`, `industry` (`{name, slug}` or null), `average_rating` (mean of review ratings to one decimal, null with no reviews), `review_count`, `short_description` and `top_review` (`title`, `slug`, `rating`, `reviewer`, `published_at`, 30-word `snippet`, or null).

| Parameter | Effect |
|---|---|
| `industry=<slug>` | Filter; repeat for several (`?industry=finance&industry=retail`) |
| `ordering=` | `name` (default), `avg_rating`, `review_count`; prefix `-` for descending. Brands without reviews sort last; ties fall back to name, then id. Unknown values sort by name |
| `page=`, `page_size=` | 20 per page by default, at most 100 |

The response sends `Cache-Control: public, max-age=30, stale-while-revalidate=120`, so browsers reuse repeat URLs for 30s (an editor's `PATCH` can take that long to show).

**Top review rule:** a brand's top review is the one with the highest rating; among equal ratings the newest (`published_at`) wins. A brand with no reviews has `top_review: null`. One windowed query picks it for every brand on the page, so a page costs three queries whatever its size; a test asserts this.

## Shared library (`libs/`)

`cauth` (JWT verification, DRF `JWTAuthentication` and `IsEditor`, roles, `deterministic_uuid`) is a versioned package. Its tests run standalone, with no Django project or service:

```bash
make lib-test
```

**How a new version reaches each service:** bump `version` in `libs/pyproject.toml`, build the wheel, change the exact pin (`cauth==X.Y.Z`) in `auth/requirements.txt` and `app/requirements.txt`, then `make up`.

**Which module each service imports:** the auth service imports `cauth.roles` and `cauth.ids.deterministic_uuid` (and `cauth.tokens` in tests); the main app imports `cauth.drf` (`JWTAuthentication`, `IsEditor`), which uses `cauth.tokens.verify`, and `deterministic_uuid` for reviewer links.

**Releasing a breaking claims change (expand-then-contract).** Tokens carry a `version` claim and `verify` accepts the current version N and N-1. (1) Release the library accepting N and N+1 and deploy it to the main app first. (2) Deploy the auth service with it; it starts issuing N+1 while N tokens still verify. (3) Once the N tokens have expired (10 minutes), release the library with N dropped. Never deploy the issuer before every consumer accepts the new version.

## Run the migration and re-run it safely

```bash
make import         # both of the below
make import-wp      # brands, reviews, industries, reviewers (main app)
make import-users   # wp_users -> auth users
```

`make import-wp` (`manage.py import_wp`) reads MariaDB inside a `READ ONLY` transaction (connection from `WP_DB_HOST`, `WP_DB_PORT`, `WP_DB_NAME`, `WP_DB_USER`, `WP_DB_PASSWORD`), keys every row on its WP id (`wp_id`; the slug is an ordinary column), and prints created, updated, unchanged, deleted and skipped counts per table. **Re-running is safe**: unchanged rows are not written, and edited rows (including renamed slugs) are updated in place. Drafts, reviews pointing at a missing brand, and ratings outside 1 to 5 are skipped. Postgres mirrors the import set: a row imported earlier that is now unpublished, trashed, deleted or invalid in WP is deleted (with its reviews), which also frees its slug. An ACF `average_rating` outside 0 to 5 is stored as null. `import_wp` never overwrites an editor's `short_description`.

| WP source | Django |
|---|---|
| `industry` term | `Industry` (`wp_id` = term_id) |
| `brand` post + ACF | `Brand`: `website_url`, `founded_year`, `headquarters` as typed columns; `industry` FK (lowest term id if WP has several) |
| ACF `average_rating` | `Brand.legacy_average_rating`, audit only. The displayed rating is derived from reviews, never stored |
| `_yoast_wpseo_title`, `_yoast_wpseo_metadesc` | `Brand.seo_title`, `Brand.seo_description` |
| `review` post + ACF | `Review`: `rating` (1 to 5 check constraint), `reviewer_location`, `brand` FK |
| `post_author` (wp_users) | `Reviewer`, pk = `deterministic_uuid('wp_user', ID)` = the auth user id; only `display_name` is kept |

**Dropped:** the ACF field-reference meta (`_website_url`, `_rating`, ...), ACF `reviewer_name` (identical to the author's display name in every row), `_wp_page_template`, and WP pages and posts (out of scope).

## Lint and format

```bash
make lint   # ruff check + format --check, biome check, stylelint (all via Docker)
make fmt    # apply the fixes
```

## Decisions I'd defend live

| # | Question | Answer | Where it lives |
|---|---|---|---|
| 1 | **Schema modeling.** A brand has an `average_rating` ACF field AND has reviews with individual ratings. Do you store the average, derive it, or both? Why? How do you handle reviewer users — full Django users, a separate Reviewer model, or denormalized strings on each review? | Derived, never stored: `average_rating` is computed from reviews (`Brand.objects.with_stats()`), and the ACF value is kept only as `legacy_average_rating` for audit. Reviewers are a separate `Reviewer` model, not Django users and not strings on each review. Its pk is `deterministic_uuid('wp_user', id)`, which is also the auth user id, so the two services link without a runtime call. Only `display_name` is kept. | `app/catalog/models.py`; R1, T3 |
| 2 | **Postmeta strategy.** `wp_postmeta` has ~30 fields per brand (including Yoast SEO). Which became first-class model fields, which became JSON, which did you drop? | First-class columns: `website_url`, `founded_year`, `headquarters`, review `rating` and `reviewer_location`, and the Yoast title and description as `seo_title` and `seo_description`. No JSON field was needed. Dropped: the ACF field-reference meta, ACF `reviewer_name` (the same as the author's display name in every row), `_wp_page_template`, and WP pages and posts. | `models.py`; R1; [Migration](#run-the-migration-and-re-run-it-safely) |
| 3 | **Migration approach.** Why this approach? How do you re-run it safely? How would you scale it to 100x the data? | `import_wp` is an upsert keyed on the WP post id, read-only against MariaDB, and it mirrors WP, so rows now unpublished or invalid are deleted. It reports created, updated, unchanged, deleted and skipped counts, and a test shows a second run changes nothing. **At 100x** (proposed, not implemented): today it reads every row into memory and writes row by row inside one transaction, which is fine for hundreds of rows and not for tens of thousands. I would read the source in id-range chunks, `bulk_create` and `bulk_update` in batches, commit per table, keep the mirror-delete step as a set of seen ids, and run it as a job instead of a one-off shell command. | `app/catalog/wp_import.py`; R2, R10 |
| 4 | **API contract.** Why this pagination shape? Why these filter/sort param names? What would change if a mobile client also consumed it? | DRF page-number pagination with the standard `count / next / previous / results` envelope. Params are `industry` (repeatable), `ordering`, `page` and `page_size` (default 20, max 100); ties break on name then id so pages never overlap, and the query count is constant per page. Reads are public JSON with `Cache-Control: public, max-age=30, stale-while-revalidate=120`. **For a mobile client** (proposed, not implemented): cursor pagination for infinite scroll, because page numbers shift when rows are added; a `fields=` option to trim the payload; a `/api/v1/` prefix, since installed apps can't be forced to update; and conditional requests (`ETag`). Token auth needs no change, since a bearer token plus the refresh endpoint already suits a mobile app. | `app/catalog/api.py`; R6 |
| 5 | **Component & state.** Where does `<BrandList />` state live? How do you handle URL-synced filter/sort state? What's your loading/error UX? | State lives in the URL (`?industry=&ordering=&page=`), read on mount and on back/forward. Filter and sort changes use `replaceState` so Back leaves the list instead of stepping through earlier filters, and page changes use `pushState`. Loading shows skeleton cards on first load, then keeps the old results dimmed with a spinner so the grid never jumps. Responses are cached per URL for 30s. Errors show a message with Retry, empty results offer Clear filters, and a superseded response is ignored. | `frontend/src/BrandList.jsx`, `url.js`; R22 to R25 |
| 6 | **SCSS architecture.** Why these partials? Why these tokens? How would a second engineer add a new component without breaking yours? | A 7-1 layout (`abstracts`, `base`, `layout`, `components`, `pages`, `main.scss`) compiled with the Sass CLI. Every design token is defined once in `abstracts/_tokens.scss` and emitted as `:root` custom properties; class names follow the WP `theme.css`. To add a component, create `components/_name.scss` and add one `@use` line to `main.scss`. | `frontend/scss/`; R21, T6, T7 |
| 7 | **Service boundary.** What does the auth service own and what does the main app own? How does the main app validate a token, and what happens when the auth service is down? How do you revoke a token or change a user's role before the token expires? | Auth owns users, password hashes and roles; the main app has no password or role column. The main app verifies RS256 tokens locally against the auth service's JWKS, cached in process. If auth is down, reads and valid-token edits keep working, and a cold cache returns 503, never an unverified write. Revocation is the 10-minute access-token lifetime plus refresh tokens stored hashed and revocable (logout or a Django admin action). A role change takes effect on the next refresh. | `auth/`, `app/config/auth.py`; R8 to R15; C2 |
| 8 | **Shared library.** What went into it and what did you keep out? How do the two services pin and upgrade it? How would you release a breaking change without deploying both services at the same moment? | `cauth` holds only JWT verification, the DRF `JWTAuthentication` and `IsEditor` classes, the role constants and `deterministic_uuid`. It has no models, views or service logic. It is a versioned wheel installed by both Dockerfiles at an exact pinned version. A breaking claims change is released expand-then-contract: the library accepts claims versions N and N-1, the consumer deploys first, then the issuer, then N-1 is dropped. Its tests run standalone. | `libs/`; R16 to R20; C4 |

## Modeling decisions, what I'd do differently, and AI defaults

### Modeling decisions.

 - The average rating is derived.
 - Reviewers are a small profile table keyed by the same deterministic id as the auth user, so the migration and the user import can run independently with no call between services.
 - The migration is an upsert keyed on `wp_id` that mirrors WordPress, so it is safe to re-run.


### What I would do differently with more time.

- Features that I left out were purposeful. Not due to a lack of time.
- I would refine the `README.md`.

But really, **with more time I would keep working on [mkit](https://github.com/michaelwayman/mkit)**

`mkit` is the plugin I built alongside this project to solve the challenge.
I have 3-5 different submissions to this challenge. All of them work. But each submission helped me to refine `mkit` and `mbuild`


### Where I chose the AI's default.
DRF generics and page-number pagination, `select_related` / `prefetch_related` for N+1, React hooks with plain `fetch` and no data library, and a Vite library-mode bundle. Defaults I replaced: unbounded pagination, hash-only passwords, and trusting token claims without a version check.

## What production would need

A WSGI server (gunicorn) instead of `runserver`, TLS, secrets management instead of the committed `.env` defaults, `DEBUG` off and `ALLOWED_HOSTS` set, static files served by a CDN or web server, signing-key rotation on a schedule with secure storage (rotation is manual today, via `make rotate-key`), rate limiting on login, HTML sanitising on import, backups and monitoring.
