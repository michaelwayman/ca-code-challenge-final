# Build brief

Build only what is listed. Out-of-scope items are decisions, not gaps. Anything else is a spec change: stop and ask. Detail: `mkit show <ID>`.

## Constraints
- C1 Docker is the only prerequisite
- C2 Auth service is its own Django project, container and database; main app stores no passwords or roles
- C3 URL slugs match WP permalinks
- C4 Shared library is small, installable, tested without either Django project
- C5 Each slice gets a fresh-context review (/mbuild:review) against its R acceptance before it is marked done

## Services and layers
- S1 Main app (Django): brands, reviews, industries, reviewer profiles, WP migration command, server-rendered pages, /api/brands/
- S2 Auth service (Django): users, password hashes, roles (reader/editor), login/token issue, JWKS, wp_users import
- S3 Shared library (Python package): JWT verification, DRF authentication and permission classes, role constants
- S4 Frontend (React + SCSS): BrandList component, SCSS source tree and compiled CSS, Vite build
- S5 Dev tooling: Makefile lint and fmt targets, Ruff, Biome and Stylelint configs

## Build
- **R2** [P0] (S1) Re-runnable WP migration command
  - `manage.py import_wp` loads all brands, reviews and industries from the WP source
  - running it twice leaves row counts identical (verified by a count query before and after)
  - updates to a WP row are reflected on re-run
  - the command prints created/updated/skipped counts
  - rows are keyed on the WP post ID, slug is an attribute
  - a test changes a slug in the source and re-runs: row updated, not duplicated
  - import_wp reads WP data read-only from MariaDB over a connection configured by env vars (host, port, db, user, password)
  - reviewer key is wp_user_uuid(wp_user_id) (uuid5 of brand-reviews:wp_user:<wp_user_id>), defined in the main app, with no call to auth and no wp_user_id column
  - import mirrors the import set: rows now unpublished, trashed, deleted or invalid are deleted with cascades
  - output has a deleted count
  - drafts, reviews with a missing brand and ratings outside 1-5 are skipped
  - ACF average_rating outside 0-5 is stored as null
  - the MariaDB read and the Postgres sync are separate steps, so the mapping can be tested without a database

## Do NOT build
- O1 WP admin and editor experience
- O2 Yoast SEO frontend output
- O3 Review submission and search
- O4 Registration, password reset, social login, MFA
- O5 Login UI
- O6 Image uploads
- O7 Pixel-matching the WP theme
- O8 Production hardening: WSGI server, TLS, secrets management, static file serving, DEBUG off

## Decided
- Outcome -> Replace the WP brand-reviews site with a Django system: app with server-rendered pages, brand-listing API, React BrandList, SCSS tree, separate auth service, shared library; migration re-runnable
- Users -> Hiring panel reviewing the repo and a 1-hour live defense; end users are visitors browsing brands/reviews and editors editing brands
- Success -> Runs from README with Docker only; WP permalinks kept; /api/brands/ filter/sort/paginate; only editor can PATCH; shared lib tests run standalone; every decision defensible. Judged on structure, not pixels
- Headline scope -> In: re-runnable migration, 3 pages, brand API, BrandList (filter/sort/states/a11y/responsive), SCSS under frontend/scss, auth service with roles, protected PATCH, shared lib, README with modeling notes. Out: WP admin, Yoast output, review submission/search, registration/reset/social/MFA, login UI, image uploads, pixel parity
- Database engine for both services -> Postgres, one container per service
- Token lifetime and key distribution -> 10 min access token, RS256, public key via cached JWKS with kid rotation (restored; rotation with overlap kept for the key ring)
- WP source: SQL dump, live DB or CSV, and how it is mounted into the containers (C1) -> Data is read directly from the live MariaDB, not a dump or CSV

## Unvalidated assumptions (flag if they break)
- A1 Revocation via short TTL
- A3 R2/R10 can run independently: reviewers link to auth users by WP user id without a runtime call
- A4 Main app JWKS cache survives restart or fails closed when auth is down and cache is cold
- A5 Refresh tokens have a bounded lifetime and a stolen one is tolerable
- A6 Token verification without iss/aud/alg pinning or refetch limits is acceptable for this scope
- A7 R20 N and N-1 claims support is worth its cost in a small library
- A8 MariaDB is reachable from the containers (compose service or host address) with Docker as the only prerequisite
