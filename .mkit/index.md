C1 [constraint] Docker is the only prerequisite
C2 [constraint] Auth service is its own Django project, container and database; main app stores no passwords or roles
C3 [constraint] URL slugs match WP permalinks
C4 [constraint] Shared library is small, installable, tested without either Django project
C5 [constraint] Each slice gets a fresh-context review (/mbuild:review) against its R acceptance before it is marked done
A1 [unvalidated] Revocation via short TTL
A2 [removed] Seed password is demo-only; migrated accounts share it
A3 [unvalidated] R2/R10 can run independently: reviewers link to auth users by WP user id without a runtime call
A4 [unvalidated] Main app JWKS cache survives restart or fails closed when auth is down and cache is cold
A5 [unvalidated] Refresh tokens have a bounded lifetime and a stolen one is tolerable
A6 [unvalidated] Token verification without iss/aud/alg pinning or refetch limits is acceptable for this scope
A7 [unvalidated] R20 N and N-1 claims support is worth its cost in a small library
A8 [unvalidated] MariaDB is reachable from the containers (compose service or host address) with Docker as the only prerequisite
S1 [active] Main app (Django)
S2 [active] Auth service (Django)
S3 [active] Shared library (Python package)
S4 [active] Frontend (React + SCSS)
S5 [active] Dev tooling
R1 [P0 done] Relational schema for brands, reviews, industries, reviewers
R2 [P0 done] Re-runnable WP migration command
R3 [P0 done] Homepage with hero and recent reviews
R4 [P0 done] Brand detail page at /brand/<slug>/
R5 [P0 done] Review detail page at /review/<slug>/
R6 [P0 done] Brand listing API with filter, sort, pagination
R7 [P1 done] Top review rule documented
R8 [P0 done] Protected brand edit endpoint
R9 [P1 done] Main app survives auth outage
R10 [P0 done] Re-runnable wp_users import
R11 [P0 done] Login issues access and refresh tokens
R12 [P0 done] Refresh and revoke
R13 [P0 done] Roles owned by auth service
R14 [P0 done] JWKS endpoint
R15 [P0 done] Auth service runs as its own container
R16 [P0 done] Installable versioned package
R17 [P0 done] Token verification
R18 [P0 done] DRF authentication and permission classes
R19 [P0 done] Library tests run standalone
R20 [P1 done] Claims version compatibility
R21 [P0 done] SCSS source tree compiling to equivalent CSS
R22 [P0 done] BrandList fetches and renders brands
R23 [P0] BrandList filter and sort with URL-synced state
R24 [P0 done] BrandList loading, empty and error states
R25 [P0 done] BrandList accessibility
R26 [P0] BrandList mounted on a Django page
R27 [P0 done] README covering run, token, migration and decisions
R28 [P0 done] WordPress password hasher
R29 [P0 done] Lint and format via Docker
O1 [active] WP admin and editor experience
O2 [active] Yoast SEO frontend output
O3 [active] Review submission and search
O4 [active] Registration, password reset, social login, MFA
O5 [active] Login UI
O6 [active] Image uploads
O7 [active] Pixel-matching the WP theme
O8 [active] Production hardening: WSGI server, TLS, secrets management, static file serving, DEBUG off
Q1 [answered] Outcome
Q2 [answered] Users
Q3 [answered] Success
Q4 [answered] Headline scope
Q5 [answered] Database engine for both services
Q6 [answered] Token lifetime and key distribution
Q7 [answered] WP source: SQL dump, live DB or CSV, and how it is mounted into the containers (C1)
T1 [active] DRF
T2 [active] JWT local verification
T3 [active] Reviewer model
T4 [active] Vite + React
T5 [active] Postgres
T6 [active] Shared SCSS, theme naming
T7 [active] SCSS 7-1 layout
T8 [active] Django runserver
T9 [active] Ruff
T10 [active] Biome
T11 [active] Stylelint
