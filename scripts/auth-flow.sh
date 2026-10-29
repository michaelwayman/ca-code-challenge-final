#!/usr/bin/env bash
# Walks the login + protected brand edit workflow with curl and checks every outcome (R33).
# Run through `make auth-flow` from the repo root, with the stack up (`make up`).
# It stops and restarts the auth service and restarts the app, and always starts auth again.
set -u
cd "$(dirname "$0")/.."

AUTH=http://localhost:8001
APP=http://localhost:8000
AUTH_USER=${AUTH_USER:-admin}
AUTH_PASS=${AUTH_PASS:-admin}
READER=authflow-reader
READER_PASS=$(head -c 12 /dev/urandom | od -An -tx1 | tr -d ' \n')
TMP=$(mktemp)
STEP=0

if [ -t 1 ]; then GREEN=$'\033[32m'; RED=$'\033[31m'; BOLD=$'\033[1m'; OFF=$'\033[0m'; else GREEN=; RED=; BOLD=; OFF=; fi

cleanup() {
  docker compose start auth >/dev/null 2>&1
  docker compose exec -T -e NAME=$READER auth python manage.py shell -c \
    "import os; from accounts.models import User; User.objects.filter(username=os.environ['NAME']).delete()" >/dev/null 2>&1
  rm -f "$TMP"
}
trap cleanup EXIT

step() { STEP=$((STEP + 1)); printf '\n%sStep %d: %s%s\n' "$BOLD" "$STEP" "$1" "$OFF"; }
say() { printf '        %s\n' "$1"; }
fail() { printf '        %s✗ %s%s\n' "$RED" "$1" "$OFF"; printf '\n%sFAILED at step %d.%s\n' "$RED" "$STEP" "$OFF"; exit 1; }
pass() { printf '        %s✓ %s%s\n' "$GREEN" "$1" "$OFF"; }

# call METHOD URL [TOKEN] [JSON]: sets CODE and BODY.
call() {
  local args=(-s -o "$TMP" -w '%{http_code}' -X "$1" "$2")
  [ -n "${3:-}" ] && args+=(-H "Authorization: Bearer $3")
  [ -n "${4:-}" ] && args+=(-H 'Content-Type: application/json' -d "$4")
  CODE=$(curl "${args[@]}") || CODE=000
  BODY=$(cat "$TMP")
}

# expect STATUS: checks the last call's status.
expect() {
  [ "$CODE" = "$1" ] || fail "expected HTTP $1, got $CODE: ${BODY:0:200}"
  pass "HTTP $CODE"
}

# expect_body TEXT: checks the last response body contains TEXT.
expect_body() {
  case "$BODY" in *"$1"*) pass "response contains: $1" ;; *) fail "response does not contain '$1': ${BODY:0:200}" ;; esac
}

login() {
  call POST $AUTH/auth/login "" "{\"username\":\"$1\",\"password\":\"$2\"}"
}
token_from_body() { printf '%s' "$BODY" | sed -n 's/.*"access_token": *"\([^"]*\)".*/\1/p'; }
patch() { call PATCH "$APP/api/brands/$SLUG/" "$1" "$2"; }

wait_for() { # wait_for URL: up to 60 seconds for a 200
  local i
  for i in $(seq 60); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' "$1")" = 200 ] && return 0
    sleep 1
  done
  fail "$1 did not come back within 60 seconds"
}

NEW="Edited by auth-flow at $(date +%H:%M:%S)"

step "Check the stack is up"
say "Looking for the auth service and the main app."
wait_for $AUTH/healthz
pass "auth answers at $AUTH"
wait_for $APP/healthz
pass "app answers at $APP"
call GET "$APP/api/brands/?page_size=1"
SLUG=$(printf '%s' "$BODY" | sed -n 's/.*"results": *\[{"name": *"[^"]*", *"slug": *"\([^"]*\)".*/\1/p')
[ -n "$SLUG" ] || SLUG=$(printf '%s' "$BODY" | sed -n 's/.*"slug": *"\([^"]*\)".*/\1/p' | head -1)
[ -n "$SLUG" ] || fail "no brand to edit; run make import first"
say "Editing the brand '$SLUG'."
call GET "$APP/api/brands/$SLUG/"
ORIGINAL=$(printf '%s' "$BODY" | sed -nE 's/.*"short_description": *"((\\.|[^"\\])*)".*/\1/p')

step "Create a throwaway reader account"
say "Imported readers have WordPress passwords we don't know, so the script makes its own ($READER)."
docker compose exec -T -e NAME=$READER -e PASS="$READER_PASS" auth python manage.py shell -c \
  "import os; from accounts.models import User; u, _ = User.objects.get_or_create(username=os.environ['NAME'], defaults={'role': 'reader'}); u.role = 'reader'; u.set_password(os.environ['PASS']); u.save()" \
  >/dev/null 2>&1 || fail "could not create the reader (is the auth container up?)"
pass "reader account ready"

step "Log in as the editor ($AUTH_USER)"
say "POST /auth/login with the editor's credentials should give an access token."
login "$AUTH_USER" "$AUTH_PASS"
expect 200
EDITOR_TOKEN=$(token_from_body)
[ -n "$EDITOR_TOKEN" ] || fail "no access_token in the response"
pass "got an access token (${#EDITOR_TOKEN} characters)"

step "Log in with the wrong password"
say "Should be refused with 401, and the message must not say which field was wrong."
login "$AUTH_USER" "not-the-password"
expect 401
expect_body "Invalid credentials"

step "PATCH with no token"
say "No Authorization header at all: 401."
patch "" "{\"short_description\":\"$NEW\"}"
expect 401

step "PATCH with a garbage token"
say "A token that is not a JWT: 401."
patch "not.a.token" "{\"short_description\":\"$NEW\"}"
expect 401

step "PATCH with a reader's token"
say "A valid token for a user whose role is reader: 403."
login $READER "$READER_PASS"
expect 200
READER_TOKEN=$(token_from_body)
patch "$READER_TOKEN" "{\"short_description\":\"$NEW\"}"
expect 403

step "PATCH with the editor's token"
say "Should update short_description and return the updated row."
patch "$EDITOR_TOKEN" "{\"short_description\":\"$NEW\"}"
expect 200
expect_body "$NEW"

step "Read the brand publicly, with no token"
say "GET stays public and must show the edited value."
call GET "$APP/api/brands/$SLUG/"
expect 200
expect_body "$NEW"

step "PATCH a brand that does not exist"
SAVED=$SLUG
SLUG=no-such-brand-$$
say "Slug '$SLUG': 404."
patch "$EDITOR_TOKEN" '{"short_description":"x"}'
expect 404
SLUG=$SAVED

step "PATCH a field that is not editable"
say "Only short_description is writable; any other key is 400 and writes nothing."
patch "$EDITOR_TOKEN" '{"name":"Hacked"}'
expect 400

step "PATCH a description over 1000 characters"
LONG=$(head -c 1001 /dev/zero | tr '\0' x)
say "1001 characters: 400."
patch "$EDITOR_TOKEN" "{\"short_description\":\"$LONG\"}"
expect 400

step "PUT the brand"
say "Only PATCH is allowed: 405."
call PUT "$APP/api/brands/$SLUG/" "$EDITOR_TOKEN" "{\"short_description\":\"$NEW\"}"
expect 405

step "Stop the auth service"
say "The app should keep serving reads and accept a token it already holds."
docker compose stop auth >/dev/null 2>&1 || fail "could not stop auth"
pass "auth is stopped"
call GET "$APP/api/brands/?page_size=1"
expect 200
patch "$EDITOR_TOKEN" "{\"short_description\":\"$NEW (auth down)\"}"
expect 200
expect_body "(auth down)"

step "Restart the app while auth is still down"
say "Its key cache is now empty and there is nothing to refetch from: writes must fail closed with 503."
docker compose restart app >/dev/null 2>&1 || fail "could not restart app"
wait_for $APP/healthz
patch "$EDITOR_TOKEN" "{\"short_description\":\"$NEW\"}"
expect 503
call GET "$APP/api/brands/?page_size=1"
expect 200
say "Reads still work."

step "Bring auth back and put the brand back as it was"
docker compose start auth >/dev/null 2>&1 || fail "could not start auth"
wait_for $AUTH/healthz
pass "auth is back"
docker compose restart app >/dev/null 2>&1 || fail "could not restart app"
wait_for $APP/healthz
login "$AUTH_USER" "$AUTH_PASS"
expect 200
EDITOR_TOKEN=$(token_from_body)
patch "$EDITOR_TOKEN" "{\"short_description\":\"$ORIGINAL\"}"
expect 200
say "short_description is back to the text the brand showed before the run (the API cannot set it back to NULL)."

printf '\n%sAll %d steps passed.%s\n' "$GREEN$BOLD" "$STEP" "$OFF"
