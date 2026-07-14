#!/usr/bin/env bash
# Smoke test for prosemend: merge the shipped example three ways, prove the
# word-level pass eliminates the false conflict that line granularity (i.e.
# classic diff3) produces, then exercise driver mode, --favor, and diff.
# Self-contained: pure stdlib, no network, idempotent (works from a clean tree).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
if [ -x "$ROOT/.venv/bin/python" ]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

# Zero runtime dependencies: running from src/ needs no install.
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/prosemend-smoke.XXXXXX")"
trap 'rm -rf "$WORKDIR"' EXIT

fail() { echo "SMOKE FAIL: $1" >&2; exit 1; }

echo "[smoke] python: $("$PYTHON" --version 2>&1)"

# 1. --version agrees with the package version.
cli_version="$("$PYTHON" -m prosemend --version)"
pkg_version="$("$PYTHON" -c 'import prosemend; print(prosemend.__version__)')"
[ "$cli_version" = "prosemend $pkg_version" ] \
  || fail "--version mismatch: '$cli_version' vs package '$pkg_version'"
echo "[smoke] version: $cli_version"

# 2. Word-level merge of the example trio is CLEAN (exit 0, both edits kept).
merged="$WORKDIR/merged.md"
if ! "$PYTHON" -m prosemend merge -q -o "$merged" \
    "$ROOT/examples/ours.md" "$ROOT/examples/base.md" "$ROOT/examples/theirs.md"; then
  fail "word-level merge of examples/ should be clean (exit 0)"
fi
grep -q "one writer outlines the notes" "$merged" || fail "ours' word edit missing"
grep -q "nothing half-baked reaches" "$merged" || fail "theirs' word edit missing"
grep -q "v1.3.0" "$merged" || fail "theirs' code-fence edit missing"
grep -q "| review | reviewer |" "$merged" || fail "ours' table edit missing"
grep -q '<<<<<<<' "$merged" && fail "clean merge must not contain markers"
echo "[smoke] word-level merge: clean, all four edits kept"

# 3. The same trio at line granularity (classic diff3) DOES conflict.
set +e
"$PYTHON" -m prosemend merge -q --granularity line -o "$WORKDIR/line.md" \
  "$ROOT/examples/ours.md" "$ROOT/examples/base.md" "$ROOT/examples/theirs.md"
rc=$?
set -e
[ "$rc" -eq 1 ] || fail "line-granularity merge should exit 1, got $rc"
grep -q '<<<<<<<' "$WORKDIR/line.md" || fail "line-granularity merge lacks markers"
echo "[smoke] line granularity: 1 false conflict, as diff3 would"

# 4. A true conflict: both sides change the same word differently.
printf 'The plan ships in May.\n' > "$WORKDIR/base.md"
printf 'The plan ships in June.\n' > "$WORKDIR/a.md"
printf 'The plan ships in July.\n' > "$WORKDIR/b.md"
set +e
out="$("$PYTHON" -m prosemend merge -q -L a.md -L base.md -L b.md \
  "$WORKDIR/a.md" "$WORKDIR/base.md" "$WORKDIR/b.md")"
rc=$?
set -e
[ "$rc" -eq 1 ] || fail "true conflict should exit 1, got $rc"
echo "$out" | grep -q '^<<<<<<< a.md$' || fail "missing labeled ours marker"
echo "$out" | grep -q '^The plan ships in June.$' || fail "ours variant not a full line"
echo "$out" | grep -q '^>>>>>>> b.md$' || fail "missing labeled theirs marker"
echo "[smoke] true conflict: markers emitted, exit 1"

# 5. --favor theirs resolves that conflict without markers.
favored="$("$PYTHON" -m prosemend merge -q --favor theirs \
  "$WORKDIR/a.md" "$WORKDIR/base.md" "$WORKDIR/b.md")" \
  || fail "--favor theirs should exit 0"
[ "$favored" = "The plan ships in July." ] || fail "--favor theirs picked wrong side"
echo "[smoke] --favor theirs: resolved"

# 6. Git merge-driver mode (%O %A %B): rewrites OURS in place.
cp "$ROOT/examples/base.md" "$WORKDIR/O"
cp "$ROOT/examples/ours.md" "$WORKDIR/A"
cp "$ROOT/examples/theirs.md" "$WORKDIR/B"
"$PYTHON" -m prosemend driver "$WORKDIR/O" "$WORKDIR/A" "$WORKDIR/B" \
  || fail "driver mode should exit 0 on the example trio"
cmp -s "$WORKDIR/A" "$merged" || fail "driver result differs from merge -o result"
echo "[smoke] driver mode: OURS rewritten in place, identical to merge -o"

# 7. Word-level diff: wdiff notation, exit 1 on change, 0 on identical.
set +e
diff_out="$("$PYTHON" -m prosemend diff "$WORKDIR/base.md" "$WORKDIR/a.md")"
rc=$?
set -e
[ "$rc" -eq 1 ] || fail "diff of changed files should exit 1, got $rc"
echo "$diff_out" | grep -q '\[-May-\]{+June+}' || fail "diff lacks wdiff notation"
"$PYTHON" -m prosemend diff "$WORKDIR/base.md" "$WORKDIR/base.md" >/dev/null \
  || fail "diff of identical files should exit 0"
echo "[smoke] diff: $diff_out"

echo "SMOKE OK"
