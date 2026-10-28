# ca-code-challenge: Spec

<!-- Source of truth. Change only with `mkit apply` or /mkit:change. IDs are stable: never renumbered or reused. -->

## Constraints

<!-- C: a limit on the solution. Fields: Kind (constraint|preference), Source, Real (real|inherited|unknown). -->

### C1. Docker is the only prerequisite
- Kind: constraint
- Source: CHALLENGE.md
- Real: real

### C2. Auth service is its own Django project, container and database; main app stores no passwords or roles
- Kind: constraint
- Source: CHALLENGE.md
- Real: real

### C3. URL slugs match WP permalinks
- Kind: constraint
- Source: CHALLENGE.md
- Real: real

### C4. Shared library is small, installable, tested without either Django project
- Kind: constraint
- Source: CHALLENGE.md
- Real: real

### C5. Each slice gets a fresh-context review (/mbuild:review) against its R acceptance before it is marked done
- Source: change
- Real: real

## Assumptions

<!-- A: something we believe but have not verified. Fields: Status (unvalidated|validated|invalid), Test (how we'd know we're wrong). -->

### A1. Revocation via short TTL
- Status: unvalidated
- Test: with refresh tokens, role change or revocation takes effect at next refresh (<=10 min); if panel wants instant effect add a denylist

### A2. Seed password is demo-only; migrated accounts share it
- Test: README flags it prominently; value comes from env var, not hardcoded in code
- Status: removed (2026-10-27, seed password no longer exists; WP hashes are migrated)

### A3. R2/R10 can run independently: reviewers link to auth users by WP user id without a runtime call
- Test: run import_wp with the auth container stopped, then import_wp_users; links resolve

### A4. Main app JWKS cache survives restart or fails closed when auth is down and cache is cold
- Test: restart main app with auth stopped, PATCH returns defined 401/503, not 500

### A5. Refresh tokens have a bounded lifetime and a stolen one is tolerable
- Test: decide refresh TTL; if instant revocation or reuse detection is wanted, add rotation (see A1)

### A6. Token verification without iss/aud/alg pinning or refetch limits is acceptable for this scope
- Test: unknown-kid tokens do not trigger more than one JWKS fetch per interval; alg none/HS256 rejected

### A7. R20 N and N-1 claims support is worth its cost in a small library
- Test: if the dual-version test is painful to write, demote R20 to a README procedure only

### A8. MariaDB is reachable from the containers (compose service or host address) with Docker as the only prerequisite
- Test: docker compose up then both imports work from a clean clone; README states where MariaDB runs

## Services and layers

<!-- S: a service or layer. Fields: Owns, Calls, When down, None (why it has no requirements). Each R names its S in Layer. -->

### S1. Main app (Django)
- Owns: brands, reviews, industries, reviewer profiles, WP migration command, server-rendered pages, /api/brands/
- Calls: Postgres (own DB), auth JWKS endpoint (key fetch, cached), shared library
- When down: public pages and GET keep working from own DB; PATCH works while cached key is valid

### S2. Auth service (Django)
- Owns: users, password hashes, roles (reader/editor), login/token issue, JWKS, wp_users import
- Calls: its own DB, shared library
- When down: no new logins; existing tokens still verify locally until expiry; main app reads unaffected

### S3. Shared library (Python package)
- Owns: JWT verification, DRF authentication and permission classes, role constants
- Calls: nothing (no Django project dependency)
- When down: n/a, build-time dependency pinned by each service

### S4. Frontend (React + SCSS)
- Owns: BrandList component, SCSS source tree and compiled CSS, Vite build
- Calls: GET /api/brands/
- When down: server-rendered pages still work without JS; list shows error state if API fails

### S5. Dev tooling
- Owns: Makefile lint and fmt targets, Ruff, Biome and Stylelint configs
- Calls: lint tools run in Docker
- When down: None: build-time tooling only

## Requirements

<!-- R: a capability a user or caller can exercise. Fields: Priority P0-P2, Layer (S<n>), Status, Source, Acceptance (observable bullets). -->

### R1. Relational schema for brands, reviews, industries, reviewers
- Priority: P0
- Status: active
- Acceptance:
  - `manage.py migrate` creates Brand, Review, Industry, Reviewer tables with FKs and no postmeta-style key/value table
  - Brand.average_rating is not a stored column and legacy ACF value sits in legacy_average_rating
  - Yoast and unused meta are either typed fields, a JSON field, or listed as dropped in the README
- Layer: S1
- Source: brief
- Built: 2026-10-27

### R2. Re-runnable WP migration command
- Priority: P0
- Status: active
- Acceptance:
  - `manage.py import_wp` loads all brands, reviews and industries from the WP source
  - running it twice leaves row counts identical (verified by a count query before and after)
  - updates to a WP row are reflected on re-run
  - the command prints created/updated/skipped counts
  - rows are keyed on the WP post ID, slug is an attribute
  - a test changes a slug in the source and re-runs: row updated, not duplicated
  - import_wp reads WP data read-only from MariaDB over a connection configured by env vars (host, port, db, user, password)
  - reviewer key is deterministic_uuid('wp_user', wp_user_id) from the shared library, with no call to auth and no wp_user_id column
- Layer: S1
- Source: brief
- Built: 2026-10-27

### R3. Homepage with hero and recent reviews
- Priority: P0
- Status: active
- Acceptance:
  - GET / returns 200 with a hero and the newest reviews in date order
  - Visual: at 375px content is one column, at 1280px reviews are in a multi-column grid
  - empty state shown when no reviews exist
- Layer: S1
- Source: brief

### R4. Brand detail page at /brand/<slug>/
- Priority: P0
- Status: active
- Acceptance:
  - every migrated brand slug returns 200 at /brand/<slug>/ showing name, industry, website, founded year, headquarters, derived rating and its reviews
  - unknown slug returns 404
  - Visual: single column at 375px, content plus sidebar at 1280px
- Layer: S1
- Source: brief

### R5. Review detail page at /review/<slug>/
- Priority: P0
- Status: active
- Acceptance:
  - every migrated review slug returns 200 at /review/<slug>/ showing title, body, rating, reviewer and a link to its brand
  - unknown slug returns 404
  - Visual: readable single column at 375px and 1280px
- Layer: S1
- Source: brief

### R6. Brand listing API with filter, sort, pagination
- Priority: P0
- Status: active
- Acceptance:
  - GET /api/brands/ returns count/next/previous/results
  - each row has name, slug, industry, average_rating, review_count, short_description, top_review snippet
  - ?industry=<slug> (repeatable) filters
  - ?ordering=-avg_rating, -review_count and name sort
  - ?page= and ?page_size= paginate with a max page size
  - unauthenticated call succeeds
  - query count is constant per page (asserted in a test)
- Layer: S1
- Source: brief
- Built: 2026-10-27

### R7. Top review rule documented
- Priority: P1
- Status: active
- Acceptance:
  - README states top = highest rating then newest
  - a test shows a brand with ties returns the newest of the highest-rated
  - brand with no reviews returns top_review null
- Layer: S1
- Source: brief
- Built: 2026-10-27

### R8. Protected brand edit endpoint
- Priority: P0
- Status: active
- Acceptance:
  - PATCH /api/brands/<slug>/ with an editor token updates short_description and returns 200
  - reader token returns 403
  - no or invalid or expired token returns 401
  - only short_description is writable
  - GET stays public
- Layer: S1
- Source: brief
- Built: 2026-10-27

### R9. Main app survives auth outage
- Priority: P1
- Status: active
- Acceptance:
  - with the auth container stopped, GET /api/brands/ and all pages still return 200
  - PATCH with a still-valid token succeeds using the cached key
  - documented in README
- Layer: S1
- Source: brief
- Built: 2026-10-27

### R10. Re-runnable wp_users import
- Priority: P0
- Status: active
- Acceptance:
  - `manage.py import_wp_users` creates one auth user per wp_users row with role mapped from WP role (administrator/editor to editor, others to reader)
  - running twice leaves user count unchanged
  - auth user pk is deterministic_uuid('wp_user', wp_user_id) from the shared library
  - no wp_user_id column
  - WP password hashes are copied verbatim into the auth user password field (stored in the auth DB only) and are unchanged by a re-run
- Layer: S2
- Source: brief
- Built: 2026-10-27

### R11. Login issues access and refresh tokens
- Priority: P0
- Status: active
- Acceptance:
  - POST /auth/login with valid credentials returns an RS256 access token (10 min) and a refresh token via curl
  - access token carries sub, role, exp, kid
  - wrong password returns 401 without revealing which field was wrong
- Layer: S2
- Source: brief
- Built: 2026-10-27

### R12. Refresh and revoke
- Priority: P0
- Status: active
- Acceptance:
  - POST /auth/refresh with a valid refresh token returns a new access token carrying the user current role
  - a user demoted in admin gets the reader role on next refresh
  - a revoked or logged-out refresh token returns 401
  - refresh tokens are stored hashed
- Layer: S2
- Source: brief
- Built: 2026-10-27

### R13. Roles owned by auth service
- Priority: P0
- Status: active
- Acceptance:
  - User has a role field with reader and editor choices
  - an operator can change it in Django admin
  - the main app database contains no role or password column (checked by a schema query)
- Layer: S2
- Source: brief
- Built: 2026-10-27

### R14. JWKS endpoint
- Priority: P0
- Status: active
- Acceptance:
  - GET /.well-known/jwks.json returns the public key set with kid, publicly and without authentication
  - adding a second key keeps old tokens verifiable until they expire
- Layer: S2
- Source: brief
- Built: 2026-10-27

### R15. Auth service runs as its own container
- Priority: P0
- Status: active
- Acceptance:
  - docker compose up starts auth and its own Postgres alongside the main app
  - main app has no credentials for the auth database
  - healthcheck URL returns 200
  - auth container starts with manage.py runserver 0.0.0.0:<port>
- Layer: S2
- Source: brief
- Built: 2026-10-27

### R16. Installable versioned package
- Priority: P0
- Status: active
- Acceptance:
  - libs/ directory has its own pyproject.toml with a version
  - `pip install` of the built wheel succeeds in a clean venv
  - both service Dockerfiles install it and pin the exact version in requirements
  - library exposes deterministic_uuid(audience, source_id) returning a UUIDv5 of source_id within a namespace derived from audience
  - a test pins known inputs to expected UUIDs and shows different audiences give different UUIDs for the same id
- Layer: S3
- Source: brief
- Built: 2026-10-27

### R17. Token verification
- Priority: P0
- Status: active
- Acceptance:
  - verify(token, jwks) returns claims for a valid RS256 token and raises distinct errors for expired, bad signature, unknown kid and malformed tokens
  - claims include a version field
- Layer: S3
- Source: brief
- Built: 2026-10-27

### R18. DRF authentication and permission classes
- Priority: P0
- Status: active
- Acceptance:
  - authentication class sets request.user from verified claims with no database lookup
  - IsEditor permits role editor only and denies reader
  - missing or invalid token yields 401 not 403
- Layer: S3
- Source: brief
- Built: 2026-10-27

### R19. Library tests run standalone
- Priority: P0
- Status: active
- Acceptance:
  - `pytest` run inside the library directory in a venv without Django project settings or either service passes
  - coverage includes expired, tampered and wrong-role cases
- Layer: S3
- Source: brief
- Built: 2026-10-27

### R20. Claims version compatibility
- Priority: P1
- Status: active
- Acceptance:
  - library accepts claims versions N and N-1
  - a test passes tokens of both versions
  - README documents the expand-then-contract release steps for a breaking change, and which module each service imports
- Layer: S3
- Source: brief
- Built: 2026-10-27

### R21. SCSS source tree compiling to equivalent CSS
- Priority: P0
- Status: active
- Acceptance:
  - `sass frontend/scss/main.scss` succeeds with no warnings
  - every selector group in reference/theme.css (.site-header, .hero, .card, .grid, .badge, .stars, .pagination, .review-item and the rest) has a home partial
  - the 37 var(--) tokens are defined once in abstracts
  - README gives the compile command and states where to add a new component partial
- Layer: S4
- Source: brief

### R22. BrandList fetches and renders brands
- Priority: P0
- Status: active
- Acceptance:
  - component renders a card per row from GET /api/brands/ showing name, slug link to /brand/<slug>/, industry, rating, review count, short description and top review snippet
  - pagination controls use page and page_size
  - Visual: 1 column at 375px, 3 columns at 1280px
  - cards use theme classes
- Layer: S4
- Source: brief

### R23. BrandList filter and sort with URL-synced state
- Priority: P0
- Status: active
- Acceptance:
  - industry checkboxes in a fieldset with legend and a sort select drive ?industry= and ?ordering=
  - changing them updates the URL via history
  - loading a URL with params restores the controls and results
  - back/forward re-fetches
  - changing filter resets to page 1
  - Visual: controls stack at 375px and sit in a row at 1280px
- Layer: S4
- Source: brief

### R24. BrandList loading, empty and error states
- Priority: P0
- Status: active
- Acceptance:
  - while fetching, skeleton or status text appears with aria-busy
  - zero results shows an empty message with a clear-filters button
  - a failed request (API stopped) shows an error message with a Retry button that refetches
  - stale responses from superseded requests are ignored
  - Visual: each state readable at 375px and 1280px
- Layer: S4
- Source: brief

### R25. BrandList accessibility
- Priority: P0
- Status: active
- Acceptance:
  - all controls reachable and operable by keyboard only with visible focus
  - results region is announced via aria-live polite
  - semantic list/heading markup
  - rating has a text alternative
  - axe scan reports no serious or critical violations
  - Visual: focus ring visible at both widths
- Layer: S4
- Source: brief

### R26. BrandList mounted on a Django page
- Priority: P0
- Status: active
- Acceptance:
  - Vite build outputs a JS bundle that a Django template at /brands/ mounts
  - README gives the build and dev commands
  - page works against the docker compose stack with no extra install
  - component has unit tests that run in CI command npm test
- Layer: S4
- Source: brief

### R27. README covering run, token, migration and decisions
- Priority: P0
- Status: active
- Acceptance:
  - README has sections to run the main app, auth service and React component
  - get a token and call PATCH with curl
  - run the library tests and how a new version reaches each service
  - run and safely re-run the migration
  - modeling decisions, what to do differently, and where AI defaults were kept
  - following it on a clean clone with docker compose up works
  - README states the project is dev-grade and lists what production would need
  - README notes WP password hashes are carried over and upgraded to Django's default on first login
  - README documents make lint and make fmt
- Layer: S1
- Source: brief

### R28. WordPress password hasher
- Priority: P0
- Status: active
- Acceptance:
  - auth Django project registers a WP hasher verifying phpass ($P$/$H$) and WP 6.8+ bcrypt ($wp$2y$) hashes
  - POST /auth/login with a migrated user's original WP password returns tokens
  - on first successful login the password is rehashed to Django's default hasher
  - wrong password returns 401
  - a test covers each hash format
- Layer: S2
- Source: change
- Built: 2026-10-27

### R29. Lint and format via Docker
- Priority: P0
- Status: active
- Acceptance:
  - make lint runs ruff check, ruff format --check, biome check and stylelint on frontend/scss in Docker with no host installs and passes on a clean tree
  - make fmt applies the fixes
  - a deliberately bad file makes make lint fail
- Layer: S5
- Source: change
- Built: 2026-10-27

## Out of scope

<!-- O: decided against, with Why and Revisit (what would change our mind). Dropped, not deferred. -->

### O1. WP admin and editor experience
- Why: explicitly out of scope in CHALLENGE.md
- Revisit: if editors need to author content outside Django admin

### O2. Yoast SEO frontend output
- Why: out of scope; data may be kept in JSON
- Revisit: if SEO parity becomes a goal

### O3. Review submission and search
- Why: out of scope
- Revisit: when write features for visitors are requested

### O4. Registration, password reset, social login, MFA
- Why: login plus roles is enough
- Revisit: before any real users

### O5. Login UI
- Why: token via curl is fine
- Revisit: when editors need a browser flow

### O6. Image uploads
- Why: placeholder boxes are fine
- Revisit: when logos are supplied

### O7. Pixel-matching the WP theme
- Why: graded on structure not byte parity
- Revisit: if visual QA is required

### O8. Production hardening: WSGI server, TLS, secrets management, static file serving, DEBUG off
- Why: project is dev-grade

## Open questions

<!-- Q: unanswered blocks `ready`. Answer with ANSWER; "you decide" is recorded as By: delegated. -->

### Q1. Outcome
- Context: Brief headline
- Answer: Replace the WP brand-reviews site with a Django system: app with server-rendered pages, brand-listing API, React BrandList, SCSS tree, separate auth service, shared library; migration re-runnable
- Decided by: you

### Q2. Users
- Context: Brief headline
- Answer: Hiring panel reviewing the repo and a 1-hour live defense; end users are visitors browsing brands/reviews and editors editing brands
- Decided by: you

### Q3. Success
- Context: Brief headline
- Answer: Runs from README with Docker only; WP permalinks kept; /api/brands/ filter/sort/paginate; only editor can PATCH; shared lib tests run standalone; every decision defensible. Judged on structure, not pixels
- Decided by: you

### Q4. Headline scope
- Context: Brief headline
- Answer: In: re-runnable migration, 3 pages, brand API, BrandList (filter/sort/states/a11y/responsive), SCSS under frontend/scss, auth service with roles, protected PATCH, shared lib, README with modeling notes. Out: WP admin, Yoast output, review submission/search, registration/reset/social/MFA, login UI, image uploads, pixel parity
- Decided by: you

### Q5. Database engine for both services
- Context: Architecture
- Answer: Postgres, one container per service
- Decided by: you

### Q6. Token lifetime and key distribution
- Context: Architecture
- Answer: 10 min access token, RS256, public key via cached JWKS with kid rotation
- Decided by: you

### Q7. WP source: SQL dump, live DB or CSV, and how it is mounted into the containers (C1)
- Answer: Data is read directly from the live MariaDB, not a dump or CSV
- Decided by: you

## Technology

<!-- T: a technology choice. Fields: Choice, Why, Alternative. -->

### T1. DRF
- Choice: Django REST Framework for API
- Why: fits shared DRF auth/permission classes, built-in pagination/filtering
- Alternative: Django Ninja, plain views

### T2. JWT local verification
- Choice: Short-lived RS256 JWT with role claim, verified locally via JWKS public key
- Why: main app survives auth outage; no per-request hop
- Alternative: opaque tokens with introspection

### T3. Reviewer model
- Choice: Reviewer profile table in main app keyed by auth user id, which is deterministic_uuid('wp_user', wp_user_id)
- Why: no passwords/roles in main app, review attribution preserved
- Alternative: denormalized name strings

### T4. Vite + React
- Choice: Vite bundle mounted into a Django template
- Why: one deployable, simple local run
- Alternative: standalone SPA

### T5. Postgres
- Choice: Postgres 16, one container per service
- Why: separate DBs as required, solid JSON and ordering
- Alternative: SQLite

### T6. Shared SCSS, theme naming
- Choice: BrandList styled by classes from the one SCSS tree, following the existing theme.css pattern (hyphenated component classes such as .card, .grid, .badge; --color-* custom properties as tokens); no CSS-in-JS or CSS modules
- Why: single styling system, matches the source theme
- Alternative: CSS modules, Tailwind

### T7. SCSS 7-1 layout
- Choice: frontend/scss/ with abstracts, base, layout, components, pages and main.scss; compiled with the Sass CLI
- Why: obvious home for each rule, new component is one partial plus one @use
- Alternative: flat partials

### T8. Django runserver
- Choice: Django services run on manage.py runserver inside their compose containers, DEBUG settings, no gunicorn or nginx
- Why: dev-grade scope, simplest local run
- Alternative: gunicorn + nginx

### T9. Ruff
- Choice: Ruff for lint and format across S1, S2, S3 with one root config
- Why: one fast tool, replaces black/flake8/isort
- Alternative: Black + flake8 + isort, mypy

### T10. Biome
- Choice: Biome for lint and format of frontend JS/JSX
- Why: one tool, fast
- Alternative: ESLint + Prettier

### T11. Stylelint
- Choice: Stylelint for the SCSS tree, since Biome has no SCSS support
- Why: guards the 7-1 layout and token rules Biome cannot see
- Alternative: sass compile only

## Deliverables trace

| Brief bullet | Covered by |
|---|---|
| Re-runnable WP migration | R2 |
| Homepage, /brand/<slug>/ and /review/<slug>/ pages | R3 R4 R5 |
| Brand-listing API with filter, sort, pagination | R6 R7 |
| BrandList with filter, sort, loading/empty/error states, accessibility, responsive | R22 R23 R24 R25 R26 |
| SCSS under frontend/scss/ | R21 |
| Auth service with token login and at least two roles | R10 R11 R12 R13 R14 R15 |
| Protected PATCH /api/brands/<slug>/ | R8 R9 |
| Shared library | R16 R17 R18 R19 R20 |
| Relational schema for brands, reviews, industries, reviewers | R1 |
| README with modeling decisions | R27 |

## Changelog

| Date | Change | By |
|---|---|---|
| 2026-10-27 | Initial spec | mkit |
| 2026-10-27 | FRAME stage brief | mkit |
| 2026-10-27 | ADD Q1: Outcome | mkit |
| 2026-10-27 | ALTER Q1 | mkit |
| 2026-10-27 | ANSWER Q1 | mkit |
| 2026-10-27 | ADD Q2: Users | mkit |
| 2026-10-27 | ANSWER Q2 | mkit |
| 2026-10-27 | ADD Q3: Success | mkit |
| 2026-10-27 | ANSWER Q3 | mkit |
| 2026-10-27 | ADD Q4: Headline scope | mkit |
| 2026-10-27 | ANSWER Q4 | mkit |
| 2026-10-27 | ADD C1: Docker is the only prerequisite | mkit |
| 2026-10-27 | ADD C2: Auth service is its own Django project, container and database; main app stores no passwords or roles | mkit |
| 2026-10-27 | ADD C3: URL slugs match WP permalinks | mkit |
| 2026-10-27 | ADD C4: Shared library is small, installable, tested without either Django project | mkit |
| 2026-10-27 | FRAME stage architecture | mkit |
| 2026-10-27 | ADD S1: Main app (Django) | mkit |
| 2026-10-27 | ADD S2: Auth service (Django) | mkit |
| 2026-10-27 | ADD S3: Shared library (Python package) | mkit |
| 2026-10-27 | ADD S4: Frontend (React + SCSS) | mkit |
| 2026-10-27 | ADD T1: DRF | mkit |
| 2026-10-27 | ADD T2: JWT local verification | mkit |
| 2026-10-27 | ADD T3: Reviewer model | mkit |
| 2026-10-27 | ADD T4: Vite + React | mkit |
| 2026-10-27 | ADD A1: Revocation via short TTL | mkit |
| 2026-10-27 | ADD Q5: Database engine for both services | mkit |
| 2026-10-27 | ADD Q6: Token lifetime and key distribution | mkit |
| 2026-10-27 | ANSWER Q5 | mkit |
| 2026-10-27 | ANSWER Q6 | mkit |
| 2026-10-27 | ADD T5: Postgres | mkit |
| 2026-10-27 | FRAME stage requirements | mkit |
| 2026-10-27 | ADD R1: Relational schema for brands, reviews, industries, reviewers | mkit |
| 2026-10-27 | ADD R2: Re-runnable WP migration command | mkit |
| 2026-10-27 | ADD R3: Homepage with hero and recent reviews | mkit |
| 2026-10-27 | ADD R4: Brand detail page at /brand/<slug>/ | mkit |
| 2026-10-27 | ADD R5: Review detail page at /review/<slug>/ | mkit |
| 2026-10-27 | ADD R6: Brand listing API with filter, sort, pagination | mkit |
| 2026-10-27 | ADD R7: Top review rule documented | mkit |
| 2026-10-27 | ADD R8: Protected brand edit endpoint | mkit |
| 2026-10-27 | ADD R9: Main app survives auth outage | mkit |
| 2026-10-27 | ALTER A1 | mkit |
| 2026-10-27 | ADD R10: Re-runnable wp_users import | mkit |
| 2026-10-27 | ADD R11: Login issues access and refresh tokens | mkit |
| 2026-10-27 | ADD R12: Refresh and revoke | mkit |
| 2026-10-27 | ADD R13: Roles owned by auth service | mkit |
| 2026-10-27 | ADD R14: JWKS endpoint | mkit |
| 2026-10-27 | ADD R15: Auth service runs as its own container | mkit |
| 2026-10-27 | ADD R16: Installable versioned package | mkit |
| 2026-10-27 | ADD R17: Token verification | mkit |
| 2026-10-27 | ADD R18: DRF authentication and permission classes | mkit |
| 2026-10-27 | ADD R19: Library tests run standalone | mkit |
| 2026-10-27 | ADD R20: Claims version compatibility | mkit |
| 2026-10-27 | ADD T6: Shared SCSS, theme naming | mkit |
| 2026-10-27 | ADD T7: SCSS 7-1 layout | mkit |
| 2026-10-27 | ADD R21: SCSS source tree compiling to equivalent CSS | mkit |
| 2026-10-27 | ADD R22: BrandList fetches and renders brands | mkit |
| 2026-10-27 | ADD R23: BrandList filter and sort with URL-synced state | mkit |
| 2026-10-27 | ADD R24: BrandList loading, empty and error states | mkit |
| 2026-10-27 | ADD R25: BrandList accessibility | mkit |
| 2026-10-27 | ADD R26: BrandList mounted on a Django page | mkit |
| 2026-10-27 | ADD O1: WP admin and editor experience | mkit |
| 2026-10-27 | ADD O2: Yoast SEO frontend output | mkit |
| 2026-10-27 | ADD O3: Review submission and search | mkit |
| 2026-10-27 | ADD O4: Registration, password reset, social login, MFA | mkit |
| 2026-10-27 | ADD O5: Login UI | mkit |
| 2026-10-27 | ADD O6: Image uploads | mkit |
| 2026-10-27 | ADD O7: Pixel-matching the WP theme | mkit |
| 2026-10-27 | TRACE R2 | mkit |
| 2026-10-27 | TRACE R3 R4 R5 | mkit |
| 2026-10-27 | TRACE R6 R7 | mkit |
| 2026-10-27 | TRACE R22 R23 R24 R25 R26 | mkit |
| 2026-10-27 | TRACE R21 | mkit |
| 2026-10-27 | TRACE R10 R11 R12 R13 R14 R15 | mkit |
| 2026-10-27 | TRACE R8 R9 | mkit |
| 2026-10-27 | TRACE R16 R17 R18 R19 R20 | mkit |
| 2026-10-27 | TRACE R1 | mkit |
| 2026-10-27 | TRACE R1 R7 | mkit |
| 2026-10-27 | ADD R27: README covering run, token, migration and decisions | mkit |
| 2026-10-27 | TRACE R27 | mkit |
| 2026-10-27 | FRAME stage confirm | mkit |
| 2026-10-27 | FRAME stage done | mkit |
| 2026-10-27 | ADD Q7: WP source: SQL dump, live DB or CSV, and how it is mounted into the containers (C1) | mkit |
| 2026-10-27 | ALTER R2 | mkit |
| 2026-10-27 | ADD A2: Seed password is demo-only; migrated accounts share it | mkit |
| 2026-10-27 | ADD A3: R2/R10 can run independently: reviewers link to auth users by WP user id without a runtime call | mkit |
| 2026-10-27 | ADD A4: Main app JWKS cache survives restart or fails closed when auth is down and cache is cold | mkit |
| 2026-10-27 | ADD A5: Refresh tokens have a bounded lifetime and a stolen one is tolerable | mkit |
| 2026-10-27 | ADD A6: Token verification without iss/aud/alg pinning or refetch limits is acceptable for this scope | mkit |
| 2026-10-27 | ADD A7: R20 N and N-1 claims support is worth its cost in a small library | mkit |
| 2026-10-27 | ANSWER Q7 | mkit |
| 2026-10-27 | ALTER R2 | mkit |
| 2026-10-27 | ALTER R10 | mkit |
| 2026-10-27 | ADD A8: MariaDB is reachable from the containers (compose service or host address) with Docker as the only prerequisite | mkit |
| 2026-10-27 | ADD T8: Django runserver | mkit |
| 2026-10-27 | ALTER R15 | mkit |
| 2026-10-27 | ADD O8: Production hardening: WSGI server, TLS, secrets management, static file serving, DEBUG off | mkit |
| 2026-10-27 | ALTER R27 | mkit |
| 2026-10-27 | ALTER R16 | mkit |
| 2026-10-27 | ALTER R10 | mkit |
| 2026-10-27 | ALTER R2 | mkit |
| 2026-10-27 | ALTER T3 | mkit |
| 2026-10-27 | ALTER R10 | mkit |
| 2026-10-27 | ADD R28: WordPress password hasher | mkit |
| 2026-10-27 | REMOVE A2: seed password no longer exists; WP hashes are migrated | mkit |
| 2026-10-27 | ALTER R27 | mkit |
| 2026-10-27 | ADD T9: Ruff | mkit |
| 2026-10-27 | ADD T10: Biome | mkit |
| 2026-10-27 | ADD T11: Stylelint | mkit |
| 2026-10-27 | ADD S5: Dev tooling | mkit |
| 2026-10-27 | ADD R29: Lint and format via Docker | mkit |
| 2026-10-27 | ADD C5: Each slice gets a fresh-context review (/mbuild:review) against its R acceptance before it is marked done | mkit |
| 2026-10-27 | ALTER R27 | mkit |
| 2026-10-27 | DONE R17 R29 | mkit |
| 2026-10-27 | DONE R18 R19 R20 | mkit |
| 2026-10-27 | DONE R11 R14 R15 | mkit |
| 2026-10-27 | DONE R28 R10 | mkit |
| 2026-10-27 | DONE R12 R13 | mkit |
| 2026-10-27 | DONE R12 R13 | mkit |
| 2026-10-27 | DONE R1 R2 R16 | mkit |
| 2026-10-27 | DONE R1 R2 R16 | mkit |
| 2026-10-27 | DONE R6 R7 | mkit |
| 2026-10-27 | DONE R8 R9 | mkit |
