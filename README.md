# Brand Reviews: WordPress to Django

A small consumer-reviews site (brands, reviews, industries) rebuilt from WordPress as a Django system: a main app with server-rendered pages and a brand-listing API, a React `<BrandList />` component, an SCSS source tree, a separate Django auth service, and a shared Python library. Docker is the only prerequisite.

**This is dev-grade by design.** It's a challenge submission, not a deployable service; see [What production would need](#what-production-would-need).

## Working on this project: mkit and mbuild

This repo is built and maintained with two Claude Code plugins, **mkit** and **mbuild**, both in [github.com/michaelwayman/mkit](https://github.com/michaelwayman/mkit) (mbuild lives in its `mbuild/` folder). I developed them alongside this project, specifically for it, and they are required to work on it the way it is set up: `SPEC.md` is the source of truth and is changed only through them, never by hand. `CLAUDE.md` tells the agent the same. The app itself runs with Docker alone; the plugins are only for changing the code. Instead of one long chat, the agent works from the written spec, one small slice at a time, which keeps token use low and makes it hard to skip a requirement.

**What they bring**
- **Fewer tokens.** The agent reads a short index (`mkit show`) and only the items it needs (`mkit show R3`), never the whole spec.
- **Small, focused context.** `mkit brief` hands the builder just the requirements, constraints and out-of-scope items for one slice, and each slice runs in a fresh session, so context never snowballs.
- **Every requirement is checked.** Each requirement has acceptance bullets. A slice is only marked done (`mkit done`) after every bullet has been run as a command, request or test and passed.
- **Nothing gets lost.** `mkit status` shows what is done, open or reopened. Bugs and ideas go to an inbox (`mkit add`) instead of derailing the current slice.
- **No scope creep.** Out-of-scope items are explicit decisions, and anything beyond a requirement stops for a `/mkit:change`.
- **Independent review.** `/mbuild:review` checks the finished work against the spec in a fresh context.
- **A paper trail.** Decisions, plans and per-slice verification records live in `SPEC.md`, `.mbuild/plan.md` and `.mbuild/auto/`. How it went in practice is in [ai-workflow.md](ai-workflow.md).

To change something: log it with `mkit add "..." --bug|--feature|--adjust`, or run `/mkit:change` when it touches scope, then `/mbuild:build`.

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

## Repository layout

```
.
├── services/
│   ├── wordpress/        # source site: wp-content (theme, mu-plugins, plugins, uploads)
│   ├── auth/             # auth service (Django): users, roles, tokens, JWKS
│   └── app/              # main app (Django): catalog, pages, /api/brands/
├── frontend/             # React BrandList + SCSS, built with Node/Vite; the app mounts frontend/dist
├── libs/
│   └── cauth/            # the shared token library
├── docs/
│   ├── research/         # reference input: the WP theme CSS the SCSS tree recreates
│   └── contracts/
│       ├── auth/         # token claims schema
│       └── app/          # brands API schema
├── scripts/              # seed scripts and the auth-flow.sh walkthrough
├── db/                   # WordPress dump that seeds MariaDB
├── docker-compose.yml    # the whole stack: WordPress + MariaDB, auth, app, and a Postgres each
├── Makefile              # every command: up, import, auth-flow, lint, tests
├── README.md             # this file
├── CHALLENGE.md          # the original challenge brief
├── ai-workflow.md        # how AI was used on this submission
├── questions.md          # live-defense questions with my answers
├── SPEC.md               # scope, constraints and decisions (managed by mkit)
├── CLAUDE.md             # instructions for Claude Code in this repo
├── .claude/              # project skills (README generation)
├── .mbuild/              # build plan and per-slice verification records
├── .mkit/                # mkit working state: brief, inbox, index
├── .env.example          # copy to .env before make up
├── .gitignore
├── .stylelintrc.json     # SCSS lint config
├── biome.json            # JS/React lint and format config
└── ruff.toml             # Python lint and format config
```


## Run the pieces

### Main app

`make up` starts `app` (Django `runserver`) with its own Postgres. `./frontend` is mounted read-only and served at `/static/`, so a frontend rebuild shows on refresh with no restart.

### Auth service

Its own Django project, container and Postgres. `import_wp_users` creates one user per `wp_users` row (id = `wp_user_uuid(ID)`, defined in its `wp_import.py`); WP `administrator` and `editor` become `editor`, everything else `reader`. **WP password hashes are carried over verbatim and upgraded to Django's default hasher on the user's first successful login** (see `services/auth/accounts/hashers.py`). Roles are edited in the Django admin; create an operator with `make operator`. The main app stores no passwords or roles.

### React component and SCSS

`frontend/src/main.jsx` mounts `<BrandList />` on `/brands/`; Django passes the industry options through `json_script`. The source is split by job:

| Folder | What is in it |
|---|---|
| `components/` | `BrandList` (wires the pieces), `BrandFilters`, `BrandResults`, `BrandCard`, `SkeletonCard`, `Stars`, `Pagination` |
| `hooks/` | `useUrlState` (list state in the URL, history and popstate), `useBrandsQuery` (fetch, cache, stale-response guard, retry) |
| `lib/` | Pure modules with no React: `constants`, `query-string`, `pagination`, `response-cache` |

Each has its own test next to it; `npm test` runs them all (`make fe-test`).

```bash
make fe-build   # npm ci + sass + vite build -> frontend/dist/css/main.css, frontend/dist/js/brand-list.js
make fe-dev     # same, rebuilding on change
make fe-test    # vitest + Testing Library + axe, in Docker
```

The SCSS tree under `frontend/scss/` is compiled with `sass frontend/scss/main.scss` (no warnings). `abstracts/_tokens.scss` is the only place design tokens are defined; `components/` has one partial per component. **To add a component:** create `components/_name.scss` and add `@use "components/name";` to `main.scss`.

## Get a token and call the protected endpoint

`PATCH /api/brands/<slug>/` needs an editor's access token from the auth service. WordPress's `admin` user is an editor; on a fresh import its password is `admin`.

```bash
TOKEN=$(curl -s -X POST localhost:8001/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}' | sed -E 's/.*"access_token": *"([^"]*)".*/\1/')
curl -s -X PATCH localhost:8000/api/brands/acme-insurance/ -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"short_description":"Fair prices, slow claims."}'
```

`make auth-flow` runs the whole workflow for you with `curl` (needs `curl` on the host and `make up` first). It prints `Step 1`, `Step 2`, and so on, with what it tries and what came back, and stops with a non-zero exit at the first outcome that is not the expected one. It covers the editor login and a successful PATCH, the public GET showing the edit, and every row in the table below, then the outage drill under "When the auth service is down". It briefly stops and restarts auth and restarts the app, always starts auth again, creates and removes a throwaway reader account, and puts the brand's description back. `AUTH_USER` and `AUTH_PASS` default to `admin` / `admin`.

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

The main app never calls the auth service per request. It verifies tokens locally with the public keys from `http://auth:8001/.well-known/jwks.json`, cached in process (`services/app/config/auth.py`), and compose deliberately has no `depends_on: auth` for it.

- **Reads** (`/api/brands/`, `/api/brands/<slug>/`, pages, `/healthz`) never touch auth and keep returning 200.
- **Writes with a still-valid token** keep working: the key set is refetched every 5 minutes, and a failed refetch keeps the last good set. Revocation therefore rests on the 10-minute token lifetime.
- **Cold cache** (main app restarted while auth is down): there is nothing to verify against, so writes fail closed with **503** `Signing keys unavailable`.
- A failed fetch is not retried for 30 seconds, and a token with an unknown `kid` triggers an immediate refetch, at most once per 30 seconds.

Try it by hand: `make auth-stop`, then a new login fails but `/api/brands/` still returns 200; with a token you already hold, a `PATCH` still succeeds; after `make app-restart` the same `PATCH` returns 503; `make auth-start` restores it. `make auth-flow` does all of this and checks it.

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

`cauth` (the typed `Claims` and `Role`, JWT verification, DRF `JWTAuthentication` and `IsEditor`) is a versioned package. Its tests run standalone, with no Django project or service:

```bash
make lib-test
```

**Release steps (bump and pin).** The version lives in one place, `__version__` in `libs/cauth/src/cauth/__init__.py` (`pyproject.toml` reads it).
1. Change the library and bump `__version__`.
2. Change the exact pin (`cauth==X.Y.Z`) in `services/auth/requirements.txt` and `services/app/requirements.txt` to match.
3. `make lib-test`.
4. `make up`. Each Dockerfile builds the wheel from `libs/cauth/` and installs only that wheel, with `--no-index`; the build fails if its version is not the pinned one, so a service can never run an unpinned local copy.

Service contracts (token claims, brands API) live in `docs/contracts/<service>/` with an owner and a version each; `make contract-test` checks the code against them.

**Which module each service imports:** the auth service imports `Claims` and `Role` from `cauth.tokens` to build and check the tokens it issues; the main app imports `cauth.drf` (`JWTAuthentication`, `IsEditor`), which uses `cauth.tokens.verify`. The WP user id to UUID rule is not in the library: each service defines it in its `wp_import.py` (`uuid5` of `brand-reviews:wp_user:<id>`) and pins the same examples in its tests.

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
| `post_author` (wp_users) | `Reviewer`, pk = `wp_user_uuid(ID)` = the auth user id; only `display_name` is kept |

**Dropped:** the ACF field-reference meta (`_website_url`, `_rating`, ...), ACF `reviewer_name` (identical to the author's display name in every row), `_wp_page_template`, and WP pages and posts (out of scope).

## Lint and format

```bash
make lint   # ruff check + format --check, biome check, stylelint (all via Docker)
make fmt    # apply the fixes
```

Ruff's `ANN` rules in `make lint` require parameter and return annotations on every function outside tests and migrations.

## Type checking

```bash
make typecheck   # mypy --strict on libs/cauth, services/auth and services/app (Docker)
```

Runs in a `python:3.12-slim` container with `mypy`, `django-stubs` and `djangorestframework-stubs` pinned in `scripts/typecheck.sh`, the services' own requirements installed, and `cauth` installed from the library source so the services are checked against its shipped types (`py.typed`). Each project has its own config in `typecheck/` because the Django plugin needs one settings module per service. It exits 0 on a clean tree and non-zero on any type error. Tests and migrations are not checked.

## Decisions I'd defend live

The eight questions from CHALLENGE.md, with my answers and where each one lives in the repo, are in [questions.md](questions.md).

## Modeling decisions, what I'd do differently, and AI defaults

### Modeling decisions

- **The average rating is derived**, never stored, so it can't disagree with the reviews. The ACF value is kept only as `legacy_average_rating`.
- **Reviewers are a small profile table** keyed by the same deterministic id as the auth user. The migration and the user import can run independently, with no call between the two services.
- **The migration is an upsert** keyed on `wp_id` that mirrors WordPress, so it is safe to re-run.

### What I would do differently with more time

- **The features I left out were deliberate, not a lack of time.** I kept to the spec's out-of-scope list: no login UI, no registration or password reset, no image uploads, no pixel-matching the WP theme.
- **The README could be tighter.** I'd cut it down further.

With more time I would keep working on [mkit](https://github.com/michaelwayman/mkit). I built it, along with `mbuild`, to solve this challenge. I've now built several submissions with it, they all work, and each one helped me refine both plugins.

### Where I chose the AI's default.
DRF generics and page-number pagination, `select_related` / `prefetch_related` for N+1, React hooks with plain `fetch` and no data library, and a Vite library-mode bundle. Defaults I replaced: unbounded pagination, hash-only passwords, and trusting token claims without a version check.

## What production would need

A WSGI server (gunicorn) instead of `runserver`, TLS, secrets management instead of the committed `.env` defaults, `DEBUG` off and `ALLOWED_HOSTS` set, static files served by a CDN or web server, signing-key rotation on a schedule with secure storage (rotation is manual today, via `make rotate-key`), rate limiting on login, HTML sanitising on import, backups and monitoring.
