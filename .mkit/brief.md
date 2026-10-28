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
- **R23** [P0] (S4) BrandList filter and sort with URL-synced state
  - industry checkboxes in a fieldset with legend and a sort select drive ?industry= and ?ordering=
  - changing industry or sort updates the URL with replaceState, so it adds no browser history entry (back after switching industries leaves the filtered view rather than stepping to the previous filter)
  - loading a URL with params restores the controls and results
  - back/forward (popstate) still restores controls and re-fetches, e.g. after a page change or an external URL
  - changing filter resets to page 1
  - Visual: controls stack at 375px and sit in a row at 1280px
  - Visual: filters read as a designed component, not browser defaults
  - industries are styled pill/chip toggles that are still real checkboxes with a clear selected state
  - the sort is a custom-styled select
  - controls sit in a card/panel with consistent spacing, type scale and radii from the shared SCSS tokens (T6)
  - Visual: hover, focus-visible and selected states are distinct and the focus ring keeps WCAG AA contrast (R25 still holds)
- **R26** [P0] (S4) BrandList mounted on a Django page
  - Vite build outputs a JS bundle that a Django template at /brands/ mounts
  - README gives the build and dev commands
  - page works against the docker compose stack with no extra install
  - component has unit tests that run in CI command npm test
  - Visual: the hero at the top of /brands/ uses the same background colour as the WordPress site's hero, via the existing shared SCSS token (R21) rather than a hardcoded value, and matches the homepage hero from R3

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
- Token lifetime and key distribution -> 10 min access token, RS256, public key via cached JWKS with kid rotation
- WP source: SQL dump, live DB or CSV, and how it is mounted into the containers (C1) -> Data is read directly from the live MariaDB, not a dump or CSV

## Unvalidated assumptions (flag if they break)
- A1 Revocation via short TTL
- A3 R2/R10 can run independently: reviewers link to auth users by WP user id without a runtime call
- A4 Main app JWKS cache survives restart or fails closed when auth is down and cache is cold
- A5 Refresh tokens have a bounded lifetime and a stolen one is tolerable
- A6 Token verification without iss/aud/alg pinning or refetch limits is acceptable for this scope
- A7 R20 N and N-1 claims support is worth its cost in a small library
- A8 MariaDB is reachable from the containers (compose service or host address) with Docker as the only prerequisite
