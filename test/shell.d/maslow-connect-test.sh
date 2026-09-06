#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

mock_bin="$tmpdir/bin"
call_log="$tmpdir/calls"
mkdir -p "$mock_bin"

cat >"$mock_bin/maslow-connect" <<'SH'
#!/bin/bash
printf '%s\0' "$@" >"$MASLOW_CONNECT_TEST_LOG"
SH

cat >"$mock_bin/omarchy-launch-webapp" <<'SH'
#!/bin/bash
printf '%s\0' "$@" >"$MASLOW_CONNECT_TEST_LOG"
SH

chmod +x "$mock_bin/maslow-connect" "$mock_bin/omarchy-launch-webapp"

run_wrapper() {
  local name=$1
  shift
  local wrapper="$tmpdir/$name"

  sed "s|/usr/bin/maslow-connect|$mock_bin/maslow-connect|g" "$ROOT/bin/$name" >"$wrapper"
  chmod +x "$wrapper"
  MASLOW_CONNECT_TEST_LOG="$call_log" PATH="$mock_bin:$PATH" "$wrapper" "$@"
}

assert_call() {
  local description=$1
  shift
  local -a actual

  mapfile -d '' -t actual <"$call_log"
  [[ ${actual[*]} == "$*" ]] || fail "$description" "expected: $*\nactual: ${actual[*]}"
  pass "$description"
}

run_wrapper omarchy-connect-setup
assert_call "setup starts only the bridge login flow" login

run_wrapper omarchy-connect-status --json
assert_call "status forwards its safe JSON flag" status --json

run_wrapper omarchy-connect-agent-list
assert_call "agent list uses the bridge registry" agent list

run_wrapper omarchy-connect-agent-enable claude-code
assert_call "agent enable forwards one explicit adapter" agent enable claude-code

run_wrapper omarchy-connect-agent-disable hermes
assert_call "agent disable forwards one explicit adapter" agent disable hermes

run_wrapper omarchy-connect-doctor codex
assert_call "doctor forwards an optional adapter" doctor codex

run_wrapper omarchy-connect-logout
assert_call "logout uses the bridge credential removal flow" logout

run_wrapper omarchy-connect-open
assert_call "open uses the existing browser app launcher" https://connect.maslow.ai

if run_wrapper omarchy-connect-agent-enable >"$tmpdir/out" 2>"$tmpdir/err"; then
  fail "agent enable rejects a missing adapter"
fi
grep -Fq 'Usage: omarchy connect agent enable <agent-id>' "$tmpdir/err" ||
  fail "agent enable reports its safe usage"
pass "agent enable rejects a missing adapter"

if rg -n -i 'api[_-]?key|refresh[_-]?token|access[_-]?token|authorization:' \
  "$ROOT"/bin/omarchy-connect-* "$ROOT/manual/maslow-connect.md"; then
  fail "Maslow Connect wrappers and help contain no credential material"
fi
pass "Maslow Connect wrappers and help contain no credential material"

grep -Fq '"setup.connect"' "$ROOT/default/omarchy/omarchy-menu.jsonc" ||
  fail "Setup menu exposes Maslow Connect separately"
grep -Fq '"action":"omarchy connect open"' "$ROOT/default/omarchy/omarchy-menu.jsonc" ||
  fail "Setup menu opens the supported command route"
pass "Setup menu exposes the supported Maslow Connect route"

for wrapper in "$ROOT"/bin/omarchy-connect-*; do
  [[ -x $wrapper ]] || fail "Maslow Connect command is executable: ${wrapper##*/}"
done
pass "Maslow Connect commands are executable"
