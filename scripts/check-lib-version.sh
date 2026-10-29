#!/bin/sh
# R31: fail when libs/ changed against BASE (default main) without a cauth version bump, or
# when the cauth pin in either service's requirements.txt is not the current version.
# Run through `make lib-check` (inside Docker).
set -eu

BASE=${BASE:-main}
INIT=libs/src/cauth/__init__.py
version_of() { sed -n 's/^__version__ = "\(.*\)"/\1/p'; }

current=$(version_of < "$INIT")
[ -n "$current" ] || { echo "no __version__ in $INIT"; exit 1; }

status=0
for svc in app auth; do
  pin=$(sed -n 's/^cauth==\([^ #]*\).*/\1/p' "$svc/requirements.txt")
  if [ "$pin" != "$current" ]; then
    echo "FAIL: $svc/requirements.txt pins cauth==$pin but libs is $current"
    status=1
  fi
done

merge_base=$(git merge-base "$BASE" HEAD) || { echo "cannot find base '$BASE'"; exit 1; }
changed=$({ git diff --name-only "$merge_base" -- libs/; git ls-files -o --exclude-standard libs/; } | sort -u)
if [ -n "$changed" ]; then
  base_version=$(git show "$merge_base:$INIT" 2>/dev/null | version_of || true)
  newest=$(printf '%s\n%s\n' "$base_version" "$current" | sort -V | tail -n 1)
  if [ "$current" = "$base_version" ] || [ "$newest" != "$current" ]; then
    echo "FAIL: libs/ changed since $BASE but cauth is still $base_version (bump __version__ in $INIT):"
    echo "$changed" | sed 's/^/  /'
    status=1
  fi
fi

[ "$status" -eq 0 ] && echo "ok: cauth $current, pinned by both services"
exit "$status"
