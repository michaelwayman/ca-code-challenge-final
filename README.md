# Brand Reviews WordPress (Interview Challenge Source)

Self-contained, reproducible WordPress site used as the source for a WP → Django migration challenge.

The site is a small consumer-reviews directory: **brands** with profile pages plus user-submitted **reviews** linked to each brand. Two custom post types, one taxonomy, ACF fields, Yoast SEO metadata.

## Quick start

```bash
cp .env.example .env
make up
```

After ~20 seconds:

- Public site: <http://localhost:8080>
- WP admin:    <http://localhost:8080/wp-admin> (`admin` / `admin`)
- phpMyAdmin:  <http://localhost:8081>
- REST root:   <http://localhost:8080/wp-json/wp/v2/>

The DB is auto-imported from `db/dump.sql` on first boot. No manual setup required for candidates.

## Stack

| Service     | Image                            | Port  | Purpose                                |
|-------------|----------------------------------|-------|----------------------------------------|
| `db`        | `mariadb:11`                     | -     | Database; auto-imports `db/dump.sql`   |
| `wordpress` | `wordpress:6.9-php8.3-apache`    | 8080  | WP + Apache + PHP                      |
| `wpcli`     | `wordpress:cli-php8.3`           | -     | Helper for re-seeding / dumping        |
| `phpmyadmin`| `phpmyadmin:5`                   | 8081  | Optional DB browser                    |

## What's committed

```
docker-compose.yml          # the stack
.env.example                # config defaults
Makefile                    # make targets
db/dump.sql                 # seeded database snapshot
scripts/seed.sh             # bootstrap script (install + plugins + seed)
wp-content/plugins/         # WP default plugins + ACF + Yoast (committed for offline reproducibility)
wp-content/mu-plugins/
  cpt.php                   # registers `brand` and `review` CPTs and `industry` taxonomy
  acf-fields.php            # registers ACF field groups in code
wp-content/themes/
  consumer-reviews/         # custom theme used by the site
```

WP core files and the default themes (e.g. twentytwentyfour) live inside the `wp_files` named volume and are recreated from the image on first boot. Only the custom `consumer-reviews` theme is committed to the repo.

## Make targets

```
make up         # start db + wordpress + phpmyadmin
make down       # stop containers (keeps volumes)
make reset      # stop AND wipe volumes (next 'up' re-imports dump.sql)
make logs       # tail wordpress + db
make wp ARGS="plugin list"   # run wp-cli inside the stack
make bootstrap  # full re-seed: WP core install + plugin install + content seed
make dump       # export the current DB to db/dump.sql
make status     # show running services
```

## Rebuilding the dump from scratch

If you change the schema or seed data:

```bash
make reset
make up
make bootstrap
make dump
git add db/dump.sql wp-content/plugins
git commit -m "Refresh seed data"
```

`make bootstrap` is idempotent enough to re-run, but the cleanest path is reset → up → bootstrap → dump.

## Content model

**`brand` CPT** at `/brand/<slug>/`
- Standard fields: title, content (body), featured image (optional)
- ACF fields: `website_url`, `founded_year`, `headquarters`, `average_rating`
- Taxonomy: `industry`
- Yoast: `_yoast_wpseo_title`, `_yoast_wpseo_metadesc` in postmeta

**`review` CPT** at `/review/<slug>/`
- Standard fields: title, content (review body), post_author (mapped to a real WP user)
- ACF fields: `rating` (1-5), `reviewer_name`, `reviewer_location`, `brand` (post object → brand id)

Seeded volume: 5 brands (one per industry), 60 reviews (12 per brand) authored by 8 reviewer users, 3 static pages (Home/About/Contact), 1 admin user.

## Django system: run it

Dev-grade by design. This is a challenge submission, not a deployable service. Docker is the only prerequisite.

```bash
cp .env.example .env
docker compose up -d --build        # WordPress + MariaDB, auth + auth-db, app + app-db
docker compose exec app python manage.py import_wp          # WP -> main app (safe to re-run)
docker compose exec auth python manage.py import_wp_users   # wp_users -> auth users (safe to re-run)
make fe-build                        # compile SCSS and bundle the React component into frontend/dist
```

| What | URL |
|---|---|
| Main app (home, `/brand/<slug>/`, `/review/<slug>/`, `/brands/`, `/api/brands/`) | <http://localhost:8000> |
| Auth service (`POST /auth/login`, JWKS) | <http://localhost:8001> |
| WordPress source | <http://localhost:8080> |

**Auth service.** Own Django project, container and Postgres. `import_wp_users` creates one user per `wp_users` row (id = `deterministic_uuid('wp_user', ID)`); WP `administrator` and `editor` become `editor`, everything else `reader`. WP password hashes are carried over verbatim and upgraded to Django's default hasher on the user's first successful login. The main app stores no passwords or roles and verifies tokens locally against the auth service's JWKS.

**Get a token and edit a brand:** see [Editing a brand](#editing-a-brand) below for the `curl` login and `PATCH`.

### React BrandList

`frontend/src/BrandList.jsx` is mounted on `/brands/` by `main.jsx`; Django passes the industry options through `json_script`. State (`industry`, `ordering`, `page`) lives in the URL.

```bash
make fe-build   # npm ci + sass + vite build -> frontend/dist/css/main.css, frontend/dist/js/brand-list.js
make fe-dev     # same, rebuilding on change
make fe-test    # npm test (vitest + Testing Library + axe), in Docker
```

`./frontend` is mounted read-only into the app container and served by `runserver` at `/static/`, so a rebuild shows on refresh with no restart.

### SCSS

`frontend/scss/` is a 7-1-style tree compiled by `sass frontend/scss/main.scss`:

- `abstracts/_tokens.scss` is the only place design tokens are defined (emitted once as `:root` custom properties); `_mixins.scss` holds the `mobile` breakpoint.
- `base/` reset, links and focus; `layout/` container, header, footer, section, grid; `components/` hero, card, stars, badge, pagination, review-item, brand-list; `pages/` brand, review, page.
- **To add a component:** create `components/_name.scss` and add `@use "components/name";` to `main.scss`.

`reference/theme.css` is the compiled WP theme; every selector group in it has a home partial above. Equivalence is structural, not byte-for-byte.

### Shared library (`libs/`)

`cauth` (JWT verification, DRF `JWTAuthentication` and `IsEditor`, roles, `deterministic_uuid`) is a versioned package. Tests run standalone, with no Django project or service:

```bash
cd libs && python -m venv .venv && .venv/bin/pip install -e '.[test]' && .venv/bin/pytest
```

A new version reaches each service by bumping `version` in `libs/pyproject.toml`, building the wheel, and changing the exact pin (`cauth==X.Y.Z`) in `auth/requirements.txt` and `app/requirements.txt`, then `docker compose up -d --build`. Claims-version rollout order is in `libs/README.md`.

### Lint and format

```bash
make lint   # ruff check + format --check, biome check, stylelint (all via Docker)
make fmt    # apply the fixes
```

### Decisions, trade-offs, what I'd do differently

- **Two Django projects, one shared library.** Auth owns users, hashes and roles (C2); the main app only verifies RS256 tokens via cached JWKS. Short 10-minute access tokens replace revocation lookups.
- **`Reviewer` keyed by `deterministic_uuid('wp_user', id)`.** Lets the migration and the auth import run independently, with no runtime call between services.
- **Average rating is derived, never stored.** The ACF `average_rating` is kept only as `legacy_average_rating` for audit.
- **Migration is an upsert keyed on `wp_id`**, mirrors WP (unpublished rows are removed), and reads MariaDB in a `READ ONLY` transaction.
- **Differently with more time:** a real `/api/industries/` endpoint instead of `json_script` options; server-side rendering of the first list page; Playwright tests against the compose stack; a refresh-token rotation story beyond the bounded lifetime; WP body HTML sanitised on import instead of rendered with `|safe`.
- **Where AI defaults were kept:** DRF generics and page-number pagination, `ModelSerializer`-style shapes, `select_related`/`prefetch_related` for N+1, React hooks with `fetch` and no data library, Vite library-mode IIFE bundle. Defaults that were replaced: unbounded pagination, hash-only passwords, trusting claims without a version check.

### What production would need (dev-grade now)

A WSGI server (gunicorn) instead of `runserver`, TLS, secrets management instead of the committed `.env` defaults, `DEBUG` off and `ALLOWED_HOSTS` set, static files served by a CDN or web server, signing-key rotation and storage, rate limiting on login, HTML sanitising on import, backups and monitoring.

## Django schema and migration (main app)

`docker compose exec app python manage.py import_wp` copies WP into the main app's Postgres. It reads MariaDB inside a `READ ONLY` transaction (connection from `WP_DB_HOST`, `WP_DB_PORT`, `WP_DB_NAME`, `WP_DB_USER`, `WP_DB_PASSWORD`), keys every row on its WP id (`wp_id`, slug is an ordinary column), and prints created/updated/unchanged/deleted/skipped per table. Re-running it is safe: unchanged rows are not written, edited rows (including renamed slugs) are updated in place. Drafts, reviews pointing at a missing brand, and ratings outside 1-5 are skipped. Postgres mirrors what was imported: a row imported earlier that is now unpublished, trashed, deleted or skipped in WP is deleted (with its reviews, and reviewers left without reviews), which also frees its slug for a new post. An ACF `average_rating` outside 0-5 is stored as null.

| WP source | Django |
|---|---|
| `industry` term | `Industry` (`wp_id` = term_id) |
| `brand` post + ACF | `Brand`: `website_url`, `founded_year`, `headquarters` as typed columns; `industry` FK (lowest term id if WP has several) |
| ACF `average_rating` | `Brand.legacy_average_rating`, audit only. The displayed rating is derived from reviews (`Brand.objects.with_stats()`), never stored |
| `_yoast_wpseo_title`, `_yoast_wpseo_metadesc` | `Brand.seo_title`, `Brand.seo_description` |
| `review` post + ACF | `Review`: `rating` (1-5 check constraint), `reviewer_location`, `brand` FK |
| `post_author` (wp_users) | `Reviewer`, pk = `deterministic_uuid('wp_user', ID)` = the auth service user id. Only `display_name` is kept; no WP id, password or role |

Dropped: the ACF field-reference meta (`_website_url`, `_rating`, ...), ACF `reviewer_name` (identical to the author's display name in every row; the reviewer FK carries it), `_wp_page_template`, and WP pages and posts (out of scope).

## Brand listing API (main app)

`GET http://localhost:8000/api/brands/` is public (no token) and returns `{count, next, previous, results}`. Each row has `name`, `slug`, `industry` (`{name, slug}` or null), `average_rating` (mean of review ratings to one decimal, null with no reviews), `review_count`, `short_description` (an editor's value exactly as saved; otherwise the WP excerpt, else the body with tags stripped, 30 words) and `top_review` (`title`, `slug`, `rating`, `reviewer`, `published_at`, 30-word `snippet`, or null).

| Parameter | Effect |
|---|---|
| `industry=<slug>` | Filter; repeat for several (`?industry=finance&industry=retail`) |
| `ordering=` | `name` (default), `avg_rating`, `review_count`; prefix `-` for descending. Brands without reviews sort last; ties fall back to name. Unknown values sort by name |
| `page=`, `page_size=` | 20 per page by default, at most 100 |

**Top review rule:** a brand's top review is the one with the highest rating; among equal ratings the newest (`published_at`) wins, and WP id breaks any remaining tie. A brand with no reviews has `top_review: null`. One windowed query (`ROW_NUMBER() OVER (PARTITION BY brand ORDER BY rating DESC, published_at DESC)`) picks it for every brand on the page, so a page costs three queries whatever its size (count, brands with stats, top reviews); a test asserts this.

### Editing a brand

`GET /api/brands/<slug>/` returns one row in the listing shape and is public: reads never look at the `Authorization` header, so a stale or broken token cannot fail them. `PATCH /api/brands/<slug>/` with `{"short_description": "..."}` needs an editor's access token from the auth service:

```sh
TOKEN=$(curl -s -X POST localhost:8001/auth/login -H 'Content-Type: application/json' \
  -d '{"username": "<editor>", "password": "<password>"}' | python3 -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')
curl -X PATCH localhost:8000/api/brands/acme-insurance/ -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"short_description": "Fair prices, slow claims."}'
```

| Request | Response |
|---|---|
| Editor token | 200 with the updated row |
| Reader token | 403 |
| No token, malformed, bad signature, expired, unknown key | 401 (`WWW-Authenticate: Bearer`) |
| Any key besides `short_description`, or none | 400; nothing is written |
| `PUT` | 405 |

`short_description` (at most 1000 characters) is stored in its own nullable column, `Brand.short_description`, and every read returns it exactly as saved: an empty string stays empty and long values are not trimmed. Until a brand is edited the column is NULL and reads derive the value from the WP excerpt or body as in the listing. `import_wp` only rewrites the excerpt, so a re-run keeps editors' values.

### When the auth service is down

The main app never calls the auth service per request. It verifies tokens locally with the public keys from `http://auth:8001/.well-known/jwks.json`, cached in process (`config/auth.py`), and compose deliberately has no `depends_on: auth` for it.

- **Reads** (`/api/brands/`, `/api/brands/<slug>/`, pages, `/healthz`) do not touch auth at all and keep returning 200.
- **Writes with a still-valid token** keep working: the key set is refetched every 5 minutes (the JWKS `max-age`), and a failed refetch keeps the last good set. Revocation therefore rests on the 10 minute token lifetime, not on reaching the auth service.
- **Cold cache** (main app restarted while auth is down): there is nothing to verify against, so writes fail closed with **503** `Signing keys unavailable`, never a 500 and never an unverified write.
- A failed fetch is not retried for 30 seconds, so an outage costs one 2 second timeout per window rather than one per request. A token with an unknown `kid` (the auth service rotated keys) triggers an immediate refetch, limited to one per 30 seconds.

Try it: `docker compose stop auth`, then repeat the `PATCH` above with a token obtained before stopping it; `docker compose restart app` and the same `PATCH` returns 503; `docker compose start auth` and it succeeds again within 30 seconds.

## Theme

The active theme is a custom one at `wp-content/themes/consumer-reviews/` (committed to the repo). It renders:

- Homepage with featured brands and recent reviews
- Brand archive (`/brand/`) — card grid
- Single brand page (`/brand/<slug>/`) — hero with industry badge, star rating, website / founded / HQ metadata, body content, and full list of customer reviews
- Review archive (`/review/`) — paginated list
- Single review (`/review/<slug>/`) — back-link to brand, star rating, reviewer name/location, body
- Page template for About / Contact / Home pages

The theme is intentionally small (~10 PHP files + one stylesheet) and is meant to show candidates what the data renders as. They are not expected to clone the theme — just to migrate the underlying data.

## Endpoints worth knowing

- `/wp-json/wp/v2/brands` — list brands (note: `rest_base` is `brands` even though post type is `brand`)
- `/wp-json/wp/v2/brands/<id>` — single brand with ACF fields under `acf`
- `/wp-json/wp/v2/reviews` — list reviews
- `/wp-json/wp/v2/industry` — taxonomy terms
- `/wp-json/wp/v2/users` — reviewer users
- `/wp-json/wp/v2/pages` — static pages

ACF fields are exposed natively via `show_in_rest: true` set in `wp-content/mu-plugins/acf-fields.php`.

## Notes for the maintainer

- The `wp-content/plugins/advanced-custom-fields/` and `wp-content/plugins/wordpress-seo/` plugin code is GPL and committed to the repo so candidates don't need internet on first boot.
- `wp-content/plugins/akismet/` and `hello.php` are WP defaults — left in place but inactive.
- The site URL is hardcoded as `http://localhost:8080` in the dump (in `wp_options.siteurl` and `home`). Changing the port requires a search/replace in `db/dump.sql` before commit, or just override via `WP_HOME` / `WP_SITEURL` constants.
- `_yoast_wpseo_*` postmeta is seeded for brand posts only.
