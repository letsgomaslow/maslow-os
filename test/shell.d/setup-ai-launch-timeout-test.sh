#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/base-test.sh"
test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT
mkdir -p "$test_tmp/bin"
cat >"$test_tmp/bin/omarchy-setup-ai-state" <<'SH'
#!/bin/bash
printf '{"completedAt":null,"deferred":false}\n'
SH
cat >"$test_tmp/bin/qs" <<'SH'
#!/bin/bash
printf 'accepted\n' >>"$LAUNCH_TEST_LOG"
if [[ ${LAUNCH_TEST_MODE:-delayed} == "not-ready" ]]; then
  echo 'Not ready to accept queries yet'
else
  sleep 3
  echo ok
fi
SH
chmod +x "$test_tmp/bin/"*
export OMARCHY_PATH="$ROOT" PATH="$test_tmp/bin:$ROOT/bin:$PATH"
export WAYLAND_DISPLAY=wayland-test LAUNCH_TEST_LOG="$test_tmp/accepted.log"
unset OMARCHY_SHELL_IPC_TIMEOUT
if omarchy-setup-ai >"$test_tmp/manual.out" 2>&1; then
  fail "ordinary two-second IPC should time out on a delayed acknowledgement"
fi
grep -q 'not responding' "$test_tmp/manual.out" || fail "manual timeout reason missing"
: >"$LAUNCH_TEST_LOG"
omarchy-setup-ai --first-login >"$test_tmp/first-login.out"
launch_calls=$(wc -l <"$LAUNCH_TEST_LOG")
(( launch_calls == 1 )) || fail "first-login launch retried the accepted summon"
grep -qx ok "$test_tmp/first-login.out" || fail "delayed first-login acknowledgement did not succeed"
pass "first-login waits for one delayed acknowledgement without a false failure"
: >"$LAUNCH_TEST_LOG"
if LAUNCH_TEST_MODE=not-ready omarchy-setup-ai --first-login >"$test_tmp/not-ready.out" 2>&1; then
  fail "first-login must not turn an immediate readiness error into success"
fi
launch_calls=$(wc -l <"$LAUNCH_TEST_LOG")
(( launch_calls == 1 )) || fail "readiness error retried the summon"
grep -q 'not ready' "$test_tmp/not-ready.out" || fail "readiness error reason missing"
pass "first-login preserves real shell failures without retries"
