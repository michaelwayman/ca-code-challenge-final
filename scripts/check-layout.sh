#!/bin/sh
# R32: fail when the repository's top-level entries, services/*, docs/* or docs/contracts/* differ
# from the "Repository layout" tree in README.md. Run through `make layout-check` (Docker).
set -eu

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Expected: the tree under "## Repository layout", glyphs turned to ASCII so awk counts bytes safely.
sed -e 's/│/|/g' -e 's/├/+/g' -e 's/└/+/g' -e 's/──/--/g' README.md | awk '
  /^## Repository layout/ { in_sec = 1; next }
  in_sec && /^## / { exit }
  in_sec && /^```/ { fence = !fence; next }
  in_sec && fence && /\+-- / {
    line = $0
    sub(/ +#.*$/, "", line)
    pos = index(line, "+-- ")
    depth = (pos - 1) / 4 + 1
    name = substr(line, pos + 4)
    sub(/\/$/, "", name)
    stack[depth] = name
    path = stack[1]
    for (i = 2; i <= depth; i++) path = path "/" stack[i]
    if (depth == 1 || path ~ /^(services|docs)\/[^\/]+$/ || path ~ /^docs\/contracts\/[^\/]+$/) print path
  }
' | LC_ALL=C sort -u > "$tmp/expected"

[ -s "$tmp/expected" ] || { echo "FAIL: no tree under '## Repository layout' in README.md"; exit 1; }

# Actual: what git sees (tracked + untracked, ignored files left out) plus empty directories.
{
  git ls-files -co --exclude-standard | sed 's/^/f /'
  find . -mindepth 1 -type d -empty -not -path './.git/*' | sed -e 's#^\./#d #'
} | awk '
  { n = split($2, p, "/"); dir = ($1 == "d") }
  { print p[1] }
  (p[1] == "services" || p[1] == "docs") && (n > 2 || (n == 2 && dir)) { print p[1] "/" p[2] }
  p[1] == "docs" && p[2] == "contracts" && (n > 3 || (n == 3 && dir)) { print p[1] "/" p[2] "/" p[3] }
' | LC_ALL=C sort -u > "$tmp/actual"

status=0
comm -13 "$tmp/actual" "$tmp/expected" | sed 's/^/FAIL: in README tree but missing on disk: /' | grep . && status=1
comm -23 "$tmp/actual" "$tmp/expected" | sed 's/^/FAIL: on disk but not in README tree: /' | grep . && status=1
[ "$status" -eq 0 ] && echo "layout ok ($(wc -l < "$tmp/expected" | tr -d ' ') entries match README)"
exit "$status"
