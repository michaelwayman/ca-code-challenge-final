---
name: readme-from-challenge
description: Use to build or rebuild README.md and questions.md from CHALLENGE.md: run/token/migration sections from the repo, the live-defense questions as a separate table, and the author's own answers kept verbatim.
---

# README from CHALLENGE.md

Builds two files so they answer what `CHALLENGE.md` asks for, and nothing else:
- `README.md`: short. Run instructions, token and protected call, library tests, migration, lint, and the author's own sections.
- `questions.md`: the "Decisions you will defend live" questions as a table (question, answer, where it lives).

Mechanical content comes from the repo. The question answers are drafted from the repo and confirmed by the user before anything is written. The author's own writing is never regenerated.

## The author's own words (never touch)
`.claude/skills/readme-from-challenge/author-answers.md` holds the sections the user wrote themselves: "Modeling decisions", "What I would do differently with more time" and "Where I chose the AI's default" (under the heading `## Modeling decisions, what I'd do differently, and AI defaults`).
- Copy that file's content, below its leading HTML comment, into `README.md` **verbatim**. Do not reword, reorder, shorten, fix, or "improve" it.
- Never draft, replace or merge these sections from the repo or from memory, even if they look incomplete.
- If the file is missing, ask the user for those answers. Do not write them yourself.
- If the user asks to change an answer, edit `author-answers.md`, then rebuild.

## 1. Read the requirements
- `CHALLENGE.md`, section "What to deliver": the bullets under `A README.md with:`.
- `CHALLENGE.md`, section "Decisions you will defend live": the numbered questions. Keep each question's text verbatim.
- Spec-mandated README content: find acceptance bullets that mention the README (`grep -n -i readme SPEC.md`, then `mkit show R<n>`). Those are required content too; dropping them makes a done R untrue. Never read SPEC.md whole.

## 2. Collect facts from the repo, not memory
Read the files and run the cheap commands to confirm they work:
- `Makefile`: the targets. The README documents `make` commands only (`make up`, `make import`, `make token`, `make patch-brand`, `make lib-test`, `make lint`, `make fmt`, ...). If a step has no target, add one to the Makefile instead of putting a raw `docker`, `curl` or `manage.py` line in the README.
- `docker-compose.yml`: service names, ports. `.env.example` for config.
- Auth: login URL and request shape (`services/auth/accounts/urls.py`, `views.py`), the seeded editor account, the protected endpoint (`services/app/catalog/api.py`).
- Library: `libs/cauth/pyproject.toml` version, `libs/cauth/README.md`, how Dockerfiles pin it.
- Migration: command names and flags (`services/app/catalog/management/commands/`, `services/auth/accounts/management/commands/`).
Report any command that fails instead of documenting it. To prove the quick start, run it in a fresh `git clone` with fresh volumes (a different directory name gives a separate compose project), then `docker compose down -v` there.

## 3. Draft the README's mechanical sections
Run the Django app, the auth service and the React component; get a token and call the protected endpoint; run the library tests and how a new version reaches each service; run the migration and re-run it safely; lint and format; what production would need; plus every spec-mandated bullet from step 1.

## 4. Draft the answers for questions.md
One row per question: `| # | Question | Answer | Where it lives |`. Source each answer from SPEC.md decisions (`mkit show` the T, Q and R items it names) and the code, and cite files. If `questions.md` already exists, start from its current answers and change only what the repo no longer supports.
- Never invent an answer. Where the repo has no evidence, write the proposal and label it "proposed, not implemented", or `TODO`, and list it for the user.
- First person, plain language.

## 5. Confirm with the user
Show the `questions.md` table and the list of TODO/proposed items. Ask the user to confirm or edit. Write nothing before this.

## 6. Write the files
- `questions.md`: a short intro, then the table.
- `README.md`: overview and quick start, run instructions, token and protected call, library tests and upgrades, migration, lint and format, a short pointer to `questions.md`, the author's sections (verbatim from `author-answers.md`), what production would need. Keep it short: link to `questions.md` instead of repeating the table.

## 7. Check
- Every README bullet in CHALLENGE.md has a heading, and every spec-mandated bullet from step 1 is covered.
- All questions appear verbatim in `questions.md`.
- The README's author sections are byte-identical to `author-answers.md` (diff them).
- The README contains no raw `docker`, `curl` or `python manage.py` commands.
- The main `make` targets run on a clean clone: `make up`, `make import` (twice), `make token`, `make patch-brand`, `make lib-test`, `make lint`.
Say what you could not verify. Do not push; the user does.
