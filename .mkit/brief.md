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
- **R22** [P0] (S4) BrandList fetches and renders brands
  - component renders a card per row from GET /api/brands/ showing name, slug link to /brand/<slug>/, industry, rating, review count, short description and top review snippet
  - pagination uses page and page_size and is a numbered list with Previous/Next: first and last page always shown, the current page and one neighbour each side, and an ellipsis for gaps (e.g. 1 … 7 [8] 9 … 18
  - near either end it shows 5 consecutive pages so there is never a lone gap)
  - each number is a button or link, the current one has aria-current=page, and Previous/Next are disabled at the ends
  - Visual: at 375px the neighbours and the Previous/Next text are dropped (e.g. ‹ 1 … [8] … 18 ›) so it fits one row
  - Visual: 1 column at 375px, 3 columns at 1280px
  - cards use theme classes
- **R24** [P0] (S4) BrandList loading, empty and error states
  - first load shows skeleton cards matching the card grid's size with aria-busy and status text for screen readers
  - on later fetches (filter, sort, page) the previous results stay visible, dimmed with aria-busy and a small spinner, and are replaced when the new data arrives
  - no layout jump while loading (results area keeps its height, heading and pagination stay mounted)
  - a response fetched in the last 30s for the same URL is shown with no loading state and no network request, and an older cached response is shown immediately and revalidated in the background, using the same window as R6's max-age
  - motion respects prefers-reduced-motion
  - zero results shows an empty message with a clear-filters button
  - a failed request (API stopped) shows an error message with a Retry button that refetches
  - stale responses from superseded requests are ignored
  - Visual: each state readable at 375px and 1280px

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
