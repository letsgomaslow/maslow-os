#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

cat >"$tmp_dir/setsid" <<'SCRIPT'
#!/bin/bash
printf '%s\n' "$*" >"$TEST_LOG"
SCRIPT
chmod +x "$tmp_dir/setsid"

export TEST_LOG="$tmp_dir/log"
export PATH="$tmp_dir:$ROOT/bin:$PATH"

"$ROOT/bin/omarchy-launch-floating-terminal-with-presentation" "echo hello"

launch=$(<"$TEST_LOG")
[[ $launch == *"xdg-terminal-exec --app-id=org.omarchy.terminal"* ]] || fail "floating terminal launches Omarchy terminal" "$launch"
pass "floating terminal launches Omarchy terminal"
[[ $launch == *'--title=Maslow OS'* ]] || fail "floating terminal uses the Maslow OS title" "$launch"
[[ $launch == *'omarchy-show-result'* ]] || fail "floating terminal presents the real command status" "$launch"
pass "floating terminal presents Maslow OS status without losing exit codes"

"$ROOT/bin/omarchy-launch-floating-terminal-with-presentation" printf '%s' 'two words'
launch=$(<"$TEST_LOG")
[[ $launch == *"printf %s two\\ words"* ]] || fail "floating terminal safely quotes argv callers" "$launch"
pass "floating terminal preserves legacy command strings and safely quotes argv callers"

set +e
"$ROOT/bin/omarchy-show-result" 130 </dev/null >/dev/null 2>&1
canceled_status=$?
"$ROOT/bin/omarchy-show-result" 7 </dev/null >/dev/null 2>&1
failed_status=$?
"$ROOT/bin/omarchy-show-result" 0 </dev/null >/dev/null 2>&1
success_status=$?
set -e
(( canceled_status == 130 )) || fail "canceled terminal workflow loses status 130"
(( failed_status == 7 )) || fail "failed terminal workflow loses its real status"
(( success_status == 0 )) || fail "successful terminal workflow does not return zero"
grep -Fq 'Needs attention. Command exited with status' "$ROOT/bin/omarchy-show-result" || fail "failed terminal workflow has no explicit attention state"
pass "terminal result presentation distinguishes success, cancellation, and failure"
