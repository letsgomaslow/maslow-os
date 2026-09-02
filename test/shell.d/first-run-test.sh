#!/bin/bash

source "$(dirname "$0")/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

mock_bin="$test_tmp/bin"
mkdir -p "$mock_bin" "$test_tmp/home"

cat >"$mock_bin/omarchy-done" <<'SH'
#!/bin/bash
[[ $1 == "check" && $2 == "first-run-user" ]]
SH
cat >"$mock_bin/omarchy-provision-user" <<'SH'
#!/bin/bash
touch "$OMARCHY_TEST_FINALIZE_CALLED"
SH
chmod +x "$mock_bin/omarchy-done" "$mock_bin/omarchy-provision-user"

finalize_called="$test_tmp/finalize-called"
HOME="$test_tmp/home" PATH="$mock_bin:$PATH" OMARCHY_TEST_FINALIZE_CALLED="$finalize_called" \
  bash "$ROOT/bin/omarchy-provision-first-run" >"$test_tmp/output"

[[ ! -e $finalize_called ]] || fail "completed first-run exits before any setup step"
grep -F 'First-run already complete' "$test_tmp/output" >/dev/null || fail "completed first-run reports its lifecycle gate"

if grep -F 'user-migration-notify-watch-enabled' "$ROOT/bin/omarchy-provision-first-run" >/dev/null; then
  fail "first-run does not track the migration watcher separately"
fi
if grep -F 'skip-first-run-update-notification' "$ROOT/install/user/first-run/wifi.sh" >/dev/null; then
  fail "first-run does not track update notifications separately"
fi

pass "first-run uses one lifecycle completion marker"

optional_marker="$test_tmp/optional-failures"
if ! (
  export HOME="$test_tmp/home"
  export OMARCHY_INSTALL="$ROOT/install"
  export MASLOW_OPTIONAL_FAILURE_FILE="$optional_marker"
  run_logged() {
    [[ $1 != *"fix-audio-mixer.sh" ]]
  }
  source "$ROOT/install/user/all.sh"
); then
  fail "optional user setup failures do not block core finalization"
fi
grep -Fq 'fix-audio-mixer.sh' "$optional_marker" || fail "optional user setup failures are not recorded for retry"
[[ $(stat -c %a "$optional_marker" 2>/dev/null || stat -f %Lp "$optional_marker") == 600 ]] || fail "optional failure state is not private"
pass "optional user setup failures remain retryable without blocking the desktop"
