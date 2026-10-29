SHELL := /bin/bash
COMPOSE := docker compose
WPCLI := $(COMPOSE) run --rm wpcli

.PHONY: help up down restart logs reset wp bootstrap dump status

help:
	@echo "Targets:"
	@echo "  up              Start db + wordpress + phpmyadmin + auth + app (each with own Postgres)"
	@echo "  down            Stop containers (preserve data)"
	@echo "  reset           Stop containers AND wipe DB volume (full cold start on next 'up')"
	@echo "  logs            Tail wordpress + db logs"
	@echo "  wp ARGS=\"...\" Run wp-cli inside the stack (e.g. make wp ARGS=\"plugin list\")"
	@echo "  bootstrap       One-shot: install WP core + plugins + seed all content"
	@echo "  dump            Export current DB to db/dump.sql"
	@echo "  status          Show running services"
	@echo "  import          Import WP data into the main app and auth service (safe to re-run)"
	@echo "  seed-demo       Add ~100 demo brands so /brands/ paginates (unseed-demo removes; import wipes them)"
	@echo "  token           Print an access token (AUTH_USER, AUTH_PASS; default admin/admin)"
	@echo "  patch-brand     Log in and PATCH a brand (SLUG=..., DESC=...)"
	@echo "  lib-test        Run the shared library tests in Docker"
	@echo "  lint / fmt      Lint or format everything in Docker"
	@echo "  fe-build        Build the SCSS and React bundle"

up:
	$(COMPOSE) up -d --build --wait db wordpress phpmyadmin auth-db auth app-db app

down:
	$(COMPOSE) down

reset:
	$(COMPOSE) down -v
	@echo "All volumes wiped. Run 'make up' then 'make import' to start fresh from db/dump.sql"

logs:
	$(COMPOSE) logs -f wordpress db

wp:
	$(WPCLI) $(ARGS)

bootstrap:
	$(COMPOSE) run --rm --entrypoint bash wpcli /scripts/seed.sh

dump:
	@mkdir -p db
	$(COMPOSE) exec db sh -c 'mariadb-dump -u root -p"$$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 --add-drop-table --skip-extended-insert "$$MYSQL_DATABASE"' > db/dump.sql
	@echo "Wrote db/dump.sql ($$(wc -l < db/dump.sql) lines)"

status:
	$(COMPOSE) ps

# --- Lint / format (Docker only; tool versions pinned) ---
RUFF_IMG := ghcr.io/astral-sh/ruff:0.8.4
NODE_IMG := node:22-alpine
RUN_NODE := docker run --rm -e NPM_CONFIG_UPDATE_NOTIFIER=false -v "$(CURDIR)":/work -w /work $(NODE_IMG) npx --yes
BIOME := $(RUN_NODE) @biomejs/biome@1.9.4
STYLELINT := docker run --rm -e NPM_CONFIG_UPDATE_NOTIFIER=false -v "$(CURDIR)":/work -w /work $(NODE_IMG) sh -c 'npm i -g --silent stylelint@16.12.0 stylelint-config-standard-scss@14.0.0 >/dev/null && stylelint --config-basedir /usr/local/lib --allow-empty-input "$$0" "$$@"'
RUFF := docker run --rm -v "$(CURDIR)":/work -w /work $(RUFF_IMG)

.PHONY: lint fmt

lint:
	$(RUFF) check .
	$(RUFF) format --check .
	$(BIOME) check --no-errors-on-unmatched frontend
	$(STYLELINT) "frontend/scss/**/*.scss"

fmt:
	-$(RUFF) check --fix .
	-$(RUFF) format .
	-$(BIOME) check --write --no-errors-on-unmatched frontend
	-$(STYLELINT) --fix "frontend/scss/**/*.scss"

# --- Frontend (Docker only): SCSS -> dist/css/main.css, Vite -> dist/js/brand-list.js ---
FE := docker run --rm -v "$(CURDIR)/frontend":/work -w /work -e NPM_CONFIG_UPDATE_NOTIFIER=false $(NODE_IMG) sh -c

.PHONY: fe-build fe-dev fe-test

fe-build:
	$(FE) 'npm ci --no-audit --no-fund --silent && npm run build'

fe-dev:
	$(FE) 'npm ci --no-audit --no-fund --silent && npm run dev'

fe-test:
	$(FE) 'npm ci --no-audit --no-fund --silent && npm test'

# --- Run the system: import, token, edit, outage drill, library tests ---
AUTH_USER ?= admin
AUTH_PASS ?= admin
SLUG ?= acme-insurance
DESC ?= Fair prices, slow claims.

.PHONY: import import-wp import-users token patch-brand admin-password operator rotate-key auth-stop auth-start app-restart lib-test seed-demo unseed-demo

import: import-wp import-users

import-wp:
	$(COMPOSE) exec -T app python manage.py import_wp

import-users:
	$(COMPOSE) exec -T auth python manage.py import_wp_users

seed-demo:
	$(COMPOSE) exec -T app python manage.py shell < scripts/seed-demo-brands.py

unseed-demo:
	$(COMPOSE) exec -T -e DEMO_CLEAR=1 app python manage.py shell < scripts/seed-demo-brands.py

token:
	@$(COMPOSE) exec -T -e AUTH_USER=$(AUTH_USER) -e AUTH_PASS=$(AUTH_PASS) auth python - < scripts/token.py

patch-brand:
	@$(COMPOSE) exec -T -e AUTH_USER=$(AUTH_USER) -e AUTH_PASS=$(AUTH_PASS) -e SLUG=$(SLUG) -e DESC="$(DESC)" app python - < scripts/patch_brand.py

admin-password:
	$(COMPOSE) exec auth python manage.py changepassword $(AUTH_USER)

operator:
	$(COMPOSE) exec auth python manage.py createsuperuser

rotate-key:
	$(COMPOSE) exec -T auth python manage.py add_signing_key

auth-stop:
	$(COMPOSE) stop auth

auth-start:
	$(COMPOSE) start auth

app-restart:
	$(COMPOSE) restart app

lib-test:
	docker run --rm -v "$(CURDIR)/libs":/work -w /work python:3.12-slim sh -c "pip install -q -e '.[test]' && pytest -q"
