---
name: readme-from-challenge
description: Use to build or rebuild README.md from CHALLENGE.md: run/token/migration sections from the repo, and the live-defense questions as a question | answer table.
---

# README from CHALLENGE.md

Builds `README.md` so it answers what `CHALLENGE.md` asks for, and nothing else. Mechanical sections come from the repo; the opinion sections are drafted from the repo and confirmed by the user before anything is written.

## 1. Read the requirements
- `CHALLENGE.md`, section "What to deliver": the bullets under `A README.md with:`.
- `CHALLENGE.md`, section "Decisions you will defend live": the numbered questions. Keep each question's text verbatim.
- Spec-mandated README content: `mkit show` the Rs whose acceptance mentions the README (find them with `grep -n -i readme SPEC.md`, then `mkit show R<n>`). Those bullets are required content too; dropping them makes a done R untrue. Never read SPEC.md whole.

## 2. Collect facts from the repo, not memory
Read the files, and run the cheap commands to confirm they work:
- `docker-compose.yml`: service names, ports, env files. `.env.example` for config.
- `Makefile`: targets worth documenting (lint, fmt, frontend build/test).
- Auth: the login URL and request shape (`auth/accounts/urls.py`, `views.py`), the seeded editor account, and the protected endpoint (`app/catalog/api.py`).
- Library: `libs/pyproject.toml` version, `libs/README.md`, how Dockerfiles pin it.
- Migration: the management command names and flags (`app/catalog/management/commands/`, `auth/accounts/management/commands/`).
Report any command that fails instead of documenting it.

## 3. Draft the mechanical sections
Run the Django app, the auth service and the React component locally; get a token and call the protected endpoint with curl; run the library tests and how a new version reaches each service; run the migration and re-run it safely; lint and format; what production would need; plus every spec-mandated bullet from step 1.

## 4. Draft the opinion sections as tables
One row per question: `| # | Question | Answer | Where it lives |`. Source each answer from SPEC.md decisions (`mkit show` the T, Q and R items it names) and the code, and cite files. Also draft the short reflection CHALLENGE.md asks for: modeling decisions, what I would do differently, and where AI defaults were kept over the author's preference, with why.
- Never invent an answer. If the repo has no evidence (for example scaling the migration 100x, or a mobile client), write `TODO` in the cell and list it for the user.
- The author's voice is first person and plain.

## 5. Confirm with the user
Show the opinion tables and the reflection as drafted, with all TODOs listed. Ask the user to confirm or edit. Write nothing to `README.md` before this.

## 6. Write README.md
Order: overview and quick start, run instructions, token and protected call, library tests and upgrades, migration, lint and format, decisions table, reflection, what production would need. Delete any README sections not asked for by CHALLENGE.md or the spec.

## 7. Check
- Every README bullet in CHALLENGE.md has a heading.
- Every spec-mandated bullet from step 1 is covered.
- All questions appear verbatim in the table.
- The main commands run: token and PATCH, migration (twice), library tests, `make lint`.
Say what you could not verify. Do not push; the user does.
