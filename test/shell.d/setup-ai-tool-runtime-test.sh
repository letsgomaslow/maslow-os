#!/bin/bash

set -euo pipefail
source "$(dirname "$0")/base-test.sh"

require_command jq
require_command setsid
require_command timeout

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT

mock_bin="$tmp_dir/bin"
package_bin="$tmp_dir/package-bin"
shadow_bin="$tmp_dir/shadow-bin"
system_bin="$tmp_dir/system-bin"
home_dir="$tmp_dir/home"
omarchy_dir="$tmp_dir/omarchy"
auth_log="$tmp_dir/auth.log"
child_pid_file="$tmp_dir/child.pid"
timeout_log="$tmp_dir/timeout.log"
mkdir -p "$mock_bin" "$package_bin" "$shadow_bin" "$system_bin" "$home_dir/.local/bin" "$omarchy_dir/install/helpers"
touch "$auth_log"
touch "$timeout_log"

cp "$ROOT/install/helpers/agent.sh" "$omarchy_dir/install/helpers/agent.sh"
cat >>"$omarchy_dir/install/helpers/agent.sh" <<'SH'
omarchy_agent_system_command_path() { printf '%s/%s' "$TEST_SYSTEM_BIN" "$1"; }
omarchy_agent_package_path() { printf '%s/%s' "$TEST_PACKAGE_BIN" "$OMARCHY_AGENT_ID"; }
SH

cat >"$mock_bin/omarchy-pkg-present" <<'SH'
#!/bin/bash
[[ " $TEST_PACKAGES " == *" $1 "* ]]
SH
cat >"$mock_bin/omarchy-pkg-available" <<'SH'
#!/bin/bash
[[ " $TEST_AVAILABLE_PACKAGES " == *" $1 "* ]]
SH
chmod +x "$mock_bin/omarchy-pkg-present" "$mock_bin/omarchy-pkg-available"

cat >"$mock_bin/timeout" <<'SH'
#!/bin/bash
printf '%s\n' "$*" >>"$TEST_TIMEOUT_LOG"
exec /usr/bin/timeout "$@"
SH
chmod +x "$mock_bin/timeout"

cat >"$package_bin/codex" <<'SH'
#!/bin/bash
printf 'codex <%s>\n' "$*" >>"$AUTH_LOG"
case "${TEST_CODEX_MODE:-signed-out}" in
signed-out) printf 'Not logged in\n' >&2; exit 1 ;;
signed-in) printf 'Logged in using ChatGPT\n' >&2 ;;
api-key) printf 'Logged in using an API key - sk-proj-***ABCDE\n' >&2 ;;
malformed) printf 'Logged in somehow with raw-secret\n' ;;
extra) printf 'Logged in using ChatGPT\nextra\n' ;;
wrong-stream) printf 'Logged in using ChatGPT\n' ;;
timeout) sleep 30 ;;
overflow) head -c 20000 /dev/zero | tr '\0' x ;;
cancel)
  sleep 30 &
  printf '%s\n' "$!" >"$CHILD_PID_FILE"
  wait
  ;;
detached)
  sleep 30 &
  printf '%s\n' "$!" >"$CHILD_PID_FILE"
  ;;
esac
SH

cat >"$package_bin/claude" <<'SH'
#!/bin/bash
printf 'claude <%s>\n' "$*" >>"$AUTH_LOG"
case "${TEST_CLAUDE_MODE:-signed-out}" in
signed-out) printf '%s\n' '{"loggedIn":false,"authMethod":"none","apiProvider":"firstParty","analyticsDisabled":false,"projectsDirectory":"/sanitized"}' ;;
signed-in) printf '%s\n' '{"loggedIn":true,"authMethod":"claude.ai","apiProvider":"firstParty","analyticsDisabled":false,"projectsDirectory":"/sanitized"}' ;;
expired-limits) printf '%s\n' '{"loggedIn":true,"authMethod":"claude.ai","apiProvider":"firstParty","analyticsDisabled":false,"projectsDirectory":"/sanitized","subscriptionType":"max","limits":{"remaining":0,"expired":true}}' ;;
malformed) printf '%s\n' '{"loggedIn":"false","token":"raw-secret"}' ;;
extra) printf '%s\n%s\n' '{"loggedIn":true}' '{"loggedIn":false}' ;;
stderr) printf '%s\n' '{"loggedIn":true}'; printf 'raw-secret\n' >&2 ;;
timeout) sleep 30 ;;
overflow) head -c 20000 /dev/zero | tr '\0' x ;;
esac
SH

cat >"$package_bin/hermes" <<'SH'
#!/bin/bash
printf 'packaged hermes invoked\n' >>"$AUTH_LOG"
exit 0
SH
chmod +x "$package_bin/codex" "$package_bin/claude" "$package_bin/hermes"

cat >"$system_bin/hermes-desktop" <<'SH'
#!/bin/bash
printf 'desktop opened\n' >>"$AUTH_LOG"
exit 0
SH
cat >"$system_bin/chatgpt" <<'SH'
#!/bin/bash
exit 0
SH
chmod +x "$system_bin/hermes-desktop" "$system_bin/chatgpt"

core_packages="openai-codex-bin claude-code hermes-agent"
available_packages="$core_packages hermes-desktop openai-codex-desktop bitwarden"

run_tool_with_path() {
  local path_value=$1
  shift
  env HOME="$home_dir" OMARCHY_PATH="$omarchy_dir" TEST_PACKAGES="${TEST_PACKAGES:-$core_packages}" \
    TEST_AVAILABLE_PACKAGES="${TEST_AVAILABLE_PACKAGES:-$available_packages}" \
    TEST_PACKAGE_BIN="$package_bin" TEST_SYSTEM_BIN="$system_bin" AUTH_LOG="$auth_log" CHILD_PID_FILE="$child_pid_file" \
    TEST_TIMEOUT_LOG="$timeout_log" \
    PATH="$path_value" OMARCHY_SETUP_AI_STATUS_TIMEOUT_SECONDS="${OMARCHY_SETUP_AI_STATUS_TIMEOUT_SECONDS:-1}" \
    TEST_CODEX_MODE="${TEST_CODEX_MODE:-signed-out}" TEST_CLAUDE_MODE="${TEST_CLAUDE_MODE:-signed-out}" TEST_HERMES_MODE="${TEST_HERMES_MODE:-ready}" \
    "$ROOT/bin/omarchy-setup-ai-tool" "$@"
}

run_tool() {
  run_tool_with_path "$package_bin:$mock_bin:/usr/bin:/bin" "$@"
}

assert_child_stopped() {
  local child_pid=$1 description=$2
  for _ in {1..30}; do
    if ! kill -0 "$child_pid" 2>/dev/null; then
      return 0
    fi
    sleep 0.05
  done
  fail "$description" "$child_pid"
}

status=$(TEST_CODEX_MODE=signed-out run_tool status codex)
[[ $(jq -r '.authentication' <<<"$status") == "signed-out" ]] || fail "shipped Codex signed-out status is not recognized" "$status"
[[ $(jq -r '.runtimeOwner + ":" + .runtimeState' <<<"$status") == "packaged:ready" ]] || fail "packaged Codex ownership is not ready" "$status"
[[ $(jq -r '["schemaVersion","id","name","supported","planned","available","installed","prerequisiteInstalled","setupOnly","userConfirmable","authentication"] - (keys) | length' <<<"$status") == 0 ]] ||
  fail "schema 1 status keys were removed" "$status"
status=$(TEST_CODEX_MODE=signed-in run_tool status codex)
[[ $(jq -r '.authentication' <<<"$status") == "signed-in" ]] || fail "shipped Codex signed-in fixture is not recognized" "$status"
status=$(TEST_CODEX_MODE=api-key run_tool status codex)
[[ $(jq -r '.authentication' <<<"$status") == "signed-in" ]] || fail "Codex API-key status is not recognized without exposing it" "$status"
[[ $status != *raw-secret* ]] || fail "Codex status exposes raw CLI output" "$status"
for mode in malformed extra wrong-stream timeout overflow; do
  status=$(TEST_CODEX_MODE=$mode run_tool status codex)
  [[ $(jq -r '.authentication' <<<"$status") == "unknown" ]] || fail "Codex $mode output can claim authentication" "$status"
  [[ $status != *raw-secret* ]] || fail "Codex $mode status exposes raw output" "$status"
done
status=$(TEST_CODEX_MODE=timeout run_tool status codex)
[[ $(jq -r '.installed == true and .runtimeOwner == "packaged" and .runtimeState == "ready" and .authentication == "unknown"' <<<"$status") == true ]] ||
  fail "Codex auth timeout erases independently discovered runtime readiness" "$status"
pass "Codex 0.152.0 status uses exact exit and bounded-output semantics"

: >"$timeout_log"
OMARCHY_SETUP_AI_STATUS_TIMEOUT_SECONDS=999 TEST_CODEX_MODE=signed-in run_tool status codex >/dev/null
grep -qF -- '--kill-after=1 9 ' "$timeout_log" || fail "numeric status timeout override is not clamped" "$(<"$timeout_log")"
: >"$timeout_log"
OMARCHY_SETUP_AI_STATUS_TIMEOUT_SECONDS=999h TEST_CODEX_MODE=signed-in run_tool status codex >/dev/null
grep -qF -- '--kill-after=1 6 ' "$timeout_log" || fail "duration suffix bypasses the seconds-only timeout" "$(<"$timeout_log")"
pass "status timeout override is seconds-only and clamped"

rm -f "$child_pid_file"
status=$(TEST_CODEX_MODE=detached run_tool status codex)
[[ $(jq -r '.authentication' <<<"$status") == "unknown" ]] || fail "empty Codex output can claim authentication" "$status"
[[ -s $child_pid_file ]] || fail "detached Codex fixture did not create a child"
assert_child_stopped "$(<"$child_pid_file")" "completed auth probe left a descendant running"
pass "completed auth probe terminates residual process-group members"

status=$(TEST_CLAUDE_MODE=signed-out run_tool status claude)
[[ $(jq -r '.authentication' <<<"$status") == "signed-out" ]] || fail "shipped Claude signed-out JSON is not recognized" "$status"
status=$(TEST_CLAUDE_MODE=signed-in run_tool status claude)
[[ $(jq -r '.authentication' <<<"$status") == "signed-in" ]] || fail "shipped Claude signed-in JSON is not recognized" "$status"
status=$(TEST_CLAUDE_MODE=expired-limits run_tool status claude)
[[ $(jq -r '.authentication' <<<"$status") == "signed-in" ]] || fail "Claude credential status is incorrectly inferred from limits" "$status"
[[ $(jq -r 'has("limits") or has("subscriptionType")' <<<"$status") == false ]] || fail "Claude status exposes account or limit fields" "$status"
for mode in malformed extra stderr timeout overflow; do
  status=$(TEST_CLAUDE_MODE=$mode run_tool status claude)
  [[ $(jq -r '.authentication' <<<"$status") == "unknown" ]] || fail "Claude $mode output can claim authentication" "$status"
  [[ $status != *raw-secret* ]] || fail "Claude $mode status exposes raw output" "$status"
done
pass "Claude 2.1.252 status reads only the structured loggedIn boolean"

status=$(run_tool_with_path "$mock_bin:/usr/bin:/bin" status codex)
[[ $(jq -r '.installed == false and .runtimeOwner == "packaged" and .runtimeState == "attention" and .reasonCode == "runtime-not-on-path"' <<<"$status") == true ]] ||
  fail "packaged command missing from PATH is not distinguished" "$status"

cat >"$shadow_bin/codex" <<'SH'
#!/bin/bash
printf 'foreign command invoked\n' >>"$AUTH_LOG"
exit 0
SH
chmod +x "$shadow_bin/codex"
: >"$auth_log"
status=$(run_tool_with_path "$shadow_bin:$package_bin:$mock_bin:/usr/bin:/bin" status codex)
[[ $(jq -r '.installed == false and .runtimeOwner == "foreign" and .runtimeState == "attention" and .reasonCode == "path-shadow" and .authentication == "unknown"' <<<"$status") == true ]] ||
  fail "foreign PATH shadow is not guarded" "$status"
[[ ! -s $auth_log ]] || fail "foreign PATH command was executed" "$(<"$auth_log")"

status=$(TEST_PACKAGES="claude-code hermes-agent" run_tool_with_path "$shadow_bin:$mock_bin:/usr/bin:/bin" status codex)
[[ $(jq -r '.runtimeOwner == "foreign" and .reasonCode == "foreign-runtime"' <<<"$status") == true ]] || fail "unpackaged foreign runtime is not identified" "$status"
status=$(TEST_PACKAGES="claude-code hermes-agent" run_tool_with_path "$mock_bin:/usr/bin:/bin" status codex)
[[ $(jq -r '.runtimeOwner == "none" and .runtimeState == "none" and .reasonCode == "missing-core"' <<<"$status") == true ]] || fail "absent runtime is not identified" "$status"
pass "runtime ownership guards missing and foreign PATH states without execution"

desktop_packages="$core_packages hermes-desktop openai-codex-desktop"
status=$(TEST_PACKAGES="$desktop_packages" run_tool status hermes)
[[ $(jq -r '.installed == false and .desktopInstalled == true and .runtimeOwner == "desktop" and .runtimeState == "attention" and .reasonCode == "desktop-setup-required" and .checkAvailable == false' <<<"$status") == true ]] ||
  fail "missing Hermes runtime falsely establishes active preparation" "$status"
status=$(TEST_PACKAGES="$desktop_packages" run_tool status hermes-desktop)
[[ $(jq -r '.installed == true and .desktopInstalled == true and .runtimeOwner == "desktop" and .runtimeState == "attention" and .reasonCode == "desktop-setup-required"' <<<"$status") == true ]] ||
  fail "Hermes Desktop card does not expose unfinished setup" "$status"

# Logs are deliberately not an adapter input. Neither a failure nor a newer
# retry message proves the current lifecycle state without supported IPC.
mkdir -p "$home_dir/.hermes/logs"
bootstrap_log="$home_dir/.hermes/logs/desktop.log"
for log_case in failed retry unknown oversized; do
  printf '%s\n' '[2026-09-05T12:00:00Z] [hermes] [bootstrap] {"type":"stage","name":"node-deps","state":"failed","error":"raw-secret"}' \
    '[2026-09-05T12:00:01Z] [hermes] [bootstrap] {"type":"failed","stage":"node-deps","error":"raw-secret"}' >"$bootstrap_log"
  case "$log_case" in
  retry) printf '%s\n' '[2026-09-05T12:01:00Z] [hermes] [bootstrap] {"type":"stage","name":"node-deps","state":"running"}' >>"$bootstrap_log" ;;
  unknown) printf '%s\n' '[hermes] [bootstrap] malformed raw-secret' >"$bootstrap_log" ;;
  oversized) head -c 1048576 /dev/zero >"$bootstrap_log" ;;
  esac
  for target in hermes hermes-desktop; do
    status=$(TEST_PACKAGES="$desktop_packages" run_tool status "$target")
    [[ $(jq -r '.runtimeState == "attention" and .reasonCode == "desktop-setup-required"' <<<"$status") == true ]] ||
      fail "$log_case bootstrap log changes conservative setup status" "$status"
    [[ $status != *raw-secret* ]] || fail "bootstrap log text leaked" "$status"
  done
done

cat >"$mock_bin/uwsm-app" <<'SH'
#!/bin/bash
[[ $1 == "--" ]] || exit 1
shift
exec "$@"
SH
chmod +x "$mock_bin/uwsm-app"
: >"$auth_log"
TEST_PACKAGES="$desktop_packages" TEST_AVAILABLE_PACKAGES="none" run_tool open hermes-desktop
for _ in {1..30}; do
  [[ -s $auth_log ]] && break
  sleep 0.05
done
[[ $(<"$auth_log") == "desktop opened" ]] || fail "unfinished desktop setup cannot open its packaged launcher" "$(<"$auth_log")"
mv "$system_bin/hermes-desktop" "$system_bin/hermes-desktop.saved"
if TEST_PACKAGES="$desktop_packages" run_tool open hermes-desktop >/dev/null 2>&1; then
  fail "desktop open accepts a missing packaged launcher"
fi
mv "$system_bin/hermes-desktop.saved" "$system_bin/hermes-desktop"
pass "unfinished desktop setup requires attention, ignores logs, and permits guided packaged launch"

mkdir -p "$home_dir/.hermes/hermes-agent"
touch "$home_dir/.hermes/hermes-agent/.hermes-bootstrap-complete"
cat >"$home_dir/.local/bin/hermes" <<SH
#!/bin/bash
# Runtime owned by $home_dir/.hermes
printf 'desktop CLI invoked\n' >>"\$AUTH_LOG"
if [[ \${1:-} == "--version" ]]; then exit 0; fi
if [[ \${1:-} == "chat" && \${2:-} == "--help" ]]; then
  case "\${TEST_HERMES_MODE:-ready}" in
  detached)
    sleep 30 &
    printf '%s\n' "\$!" >"\$CHILD_PID_FILE"
    printf '%s\n' '--oneshot'
    ;;
  cancel)
    sleep 30 &
    printf '%s\n' "\$!" >"\$CHILD_PID_FILE"
    wait
    ;;
  *) printf '%s\n' '--oneshot' ;;
  esac
  exit 0
fi
exit 1
SH
chmod +x "$home_dir/.local/bin/hermes"
printf '%s\n' '[2026-09-05T12:00:01Z] [hermes] [bootstrap] {"type":"failed","stage":"node-deps","error":"raw-secret"}' >"$bootstrap_log"
status=$(TEST_PACKAGES="$desktop_packages" run_tool_with_path "$home_dir/.local/bin:$package_bin:$mock_bin:/usr/bin:/bin" status hermes)
[[ $(jq -r '.installed == true and .desktopInstalled == true and .runtimeOwner == "desktop" and .runtimeState == "ready" and .authentication == "unknown"' <<<"$status") == true ]] ||
  fail "Hermes Desktop takeover is not recognized as the owning ready runtime" "$status"
status=$(TEST_PACKAGES="$desktop_packages" run_tool_with_path "$home_dir/.local/bin:$package_bin:$mock_bin:/usr/bin:/bin" status hermes-desktop)
[[ $(jq -r '.desktopInstalled == true and .runtimeState == "ready"' <<<"$status") == true ]] || fail "ready Hermes Desktop card is not recognized" "$status"

rm -f "$child_pid_file"
status=$(TEST_HERMES_MODE=detached TEST_PACKAGES="$desktop_packages" run_tool_with_path "$home_dir/.local/bin:$package_bin:$mock_bin:/usr/bin:/bin" status hermes)
[[ $(jq -r '.runtimeOwner == "desktop" and .runtimeState == "ready"' <<<"$status") == true ]] || fail "bounded Hermes capability fixture is not ready" "$status"
[[ -s $child_pid_file ]] || fail "detached Hermes capability fixture did not create a child"
assert_child_stopped "$(<"$child_pid_file")" "completed Hermes capability probe left a descendant running"

rm "$home_dir/.hermes/hermes-agent/.hermes-bootstrap-complete"
status=$(TEST_PACKAGES="$desktop_packages" run_tool_with_path "$home_dir/.local/bin:$package_bin:$mock_bin:/usr/bin:/bin" status hermes)
[[ $(jq -r '.installed == false and .runtimeOwner == "desktop" and .runtimeState == "attention" and .reasonCode == "desktop-runtime-attention"' <<<"$status") == true ]] ||
  fail "inconsistent Hermes Desktop ownership does not require attention" "$status"

: >"$auth_log"
TEST_PACKAGES="$desktop_packages" run_tool_with_path "$home_dir/.local/bin:$package_bin:$mock_bin:/usr/bin:/bin" open hermes-desktop
for _ in {1..30}; do
  [[ -s $auth_log ]] && break
  sleep 0.05
done
[[ $(<"$auth_log") == "desktop opened" ]] || fail "broken runtime blocks guided desktop opening or executes a CLI" "$(<"$auth_log")"
pass "desktop recovery opens its packaged app despite incomplete CLI ownership"

status=$(TEST_PACKAGES="$desktop_packages" run_tool status chatgpt-desktop)
[[ $(jq -r '.installed == true and .desktopInstalled == true and .runtimeOwner == "desktop" and .runtimeState == "ready" and .authentication == "unknown"' <<<"$status") == true ]] ||
  fail "ChatGPT Desktop installed state is not recognized" "$status"
status=$(TEST_PACKAGES="$core_packages" run_tool status chatgpt-desktop)
[[ $(jq -r '.installed == false and .desktopInstalled == false and .runtimeOwner == "none" and .runtimeState == "attention"' <<<"$status") == true ]] ||
  fail "partial ChatGPT Desktop state is not recognized" "$status"
status=$(TEST_PACKAGES="$desktop_packages" TEST_AVAILABLE_PACKAGES="none" run_tool status chatgpt-desktop)
[[ $(jq -r '.installed == true and .available == false and .runtimeState == "ready"' <<<"$status") == true ]] || fail "installed desktop is hidden when its repository is unavailable" "$status"
pass "desktop states distinguish app presence, preparation, readiness, and attention"

: >"$auth_log"
rm -f "$child_pid_file"
env HOME="$home_dir" OMARCHY_PATH="$omarchy_dir" TEST_PACKAGES="$core_packages" TEST_PACKAGE_BIN="$package_bin" \
  TEST_SYSTEM_BIN="$system_bin" AUTH_LOG="$auth_log" CHILD_PID_FILE="$child_pid_file" \
  TEST_TIMEOUT_LOG="$timeout_log" \
  PATH="$package_bin:$mock_bin:/usr/bin:/bin" OMARCHY_SETUP_AI_STATUS_TIMEOUT_SECONDS=30 TEST_CODEX_MODE=cancel \
  "$ROOT/bin/omarchy-setup-ai-tool" status codex >"$tmp_dir/cancel.out" 2>"$tmp_dir/cancel.err" &
adapter_pid=$!
for _ in {1..50}; do
  [[ -s $child_pid_file ]] && break
  sleep 0.05
done
[[ -s $child_pid_file ]] || fail "cancellation fixture did not start a child"
child_pid=$(<"$child_pid_file")
kill -TERM "$adapter_pid"
set +e
wait "$adapter_pid"
cancel_status=$?
set -e
(( cancel_status == 130 )) || fail "cancelled auth probe did not exit 130" "$cancel_status"
assert_child_stopped "$child_pid" "cancelled auth probe left an orphan process"
pass "auth probe cancellation terminates its process group without an orphan"

touch "$home_dir/.hermes/hermes-agent/.hermes-bootstrap-complete"
rm -f "$child_pid_file"
env HOME="$home_dir" OMARCHY_PATH="$omarchy_dir" TEST_PACKAGES="$desktop_packages" TEST_AVAILABLE_PACKAGES="$available_packages" \
  TEST_PACKAGE_BIN="$package_bin" TEST_SYSTEM_BIN="$system_bin" AUTH_LOG="$auth_log" CHILD_PID_FILE="$child_pid_file" \
  TEST_TIMEOUT_LOG="$timeout_log" \
  PATH="$home_dir/.local/bin:$package_bin:$mock_bin:/usr/bin:/bin" OMARCHY_SETUP_AI_STATUS_TIMEOUT_SECONDS=30 TEST_HERMES_MODE=cancel \
  "$ROOT/bin/omarchy-setup-ai-tool" status hermes >"$tmp_dir/hermes-cancel.out" 2>"$tmp_dir/hermes-cancel.err" &
adapter_pid=$!
for _ in {1..50}; do
  [[ -s $child_pid_file ]] && break
  sleep 0.05
done
[[ -s $child_pid_file ]] || fail "Hermes cancellation fixture did not start a child"
child_pid=$(<"$child_pid_file")
kill -TERM "$adapter_pid"
set +e
wait "$adapter_pid"
cancel_status=$?
set -e
(( cancel_status == 130 )) || fail "cancelled Hermes capability probe did not exit 130" "$cancel_status"
assert_child_stopped "$child_pid" "cancelled Hermes capability probe left an orphan process"
pass "Hermes capability cancellation terminates its process group without an orphan"
