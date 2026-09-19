#!/bin/bash

set -euo pipefail
source "$(dirname "$0")/base-test.sh"

require_command jq

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT

mock_bin="$tmp_dir/bin"
package_bin="$tmp_dir/package-bin"
system_bin="$tmp_dir/system-bin"
home_dir="$tmp_dir/home"
omarchy_dir="$tmp_dir/omarchy"
log_file="$tmp_dir/commands.log"
mkdir -p "$mock_bin" "$package_bin" "$system_bin" "$home_dir" "$omarchy_dir/install/helpers"
touch "$log_file"

cp "$ROOT/install/helpers/agent.sh" "$omarchy_dir/install/helpers/agent.sh"
cat >>"$omarchy_dir/install/helpers/agent.sh" <<'SH'
omarchy_agent_system_command_path() { printf '%s/%s' "$TEST_SYSTEM_BIN" "$1"; }
omarchy_agent_package_path() { printf '%s/%s' "$TEST_PACKAGE_BIN" "$OMARCHY_AGENT_ID"; }
SH

make_log_mock() {
  local directory=$1 name=$2
  cat >"$directory/$name" <<'SH'
#!/bin/bash
printf '%s' "$(basename "$0")" >>"$COMMAND_LOG"
printf ' <%s>' "$@" >>"$COMMAND_LOG"
printf '\n' >>"$COMMAND_LOG"
exit 0
SH
  chmod +x "$directory/$name"
}

cat >"$mock_bin/omarchy-pkg-present" <<'SH'
#!/bin/bash
[[ " $TEST_PACKAGES " == *" $1 "* ]]
SH
cat >"$mock_bin/omarchy-pkg-available" <<'SH'
#!/bin/bash
[[ " $TEST_AVAILABLE_PACKAGES " == *" $1 "* ]]
SH
chmod +x "$mock_bin/omarchy-pkg-present" "$mock_bin/omarchy-pkg-available"

for command in omarchy-install-and-launch omarchy-launch-floating-terminal-with-presentation; do
  make_log_mock "$mock_bin" "$command"
done
for command in setsid uwsm-app gtk-launch; do
  make_log_mock "$mock_bin" "$command"
done
for command in codex claude hermes; do
  make_log_mock "$package_bin" "$command"
done
for command in hermes-desktop chatgpt; do
  make_log_mock "$system_bin" "$command"
done

core_packages="bitwarden openai-codex-bin claude-code hermes-agent"
available_packages="$core_packages hermes-desktop openai-codex-desktop"

run_tool() {
  HOME="$home_dir" OMARCHY_PATH="$omarchy_dir" COMMAND_LOG="$log_file" \
    TEST_PACKAGES="${TEST_PACKAGES:-$core_packages}" TEST_AVAILABLE_PACKAGES="${TEST_AVAILABLE_PACKAGES:-$available_packages}" TEST_PACKAGE_BIN="$package_bin" TEST_SYSTEM_BIN="$system_bin" \
    PATH="$package_bin:$mock_bin:$PATH" "$ROOT/bin/omarchy-setup-ai-tool" "$@"
}

assert_last_call() {
  local expected=$1 description=$2
  [[ $(tail -n 1 "$log_file") == "$expected" ]] || fail "$description" "$(<"$log_file")"
}

catalog=$(run_tool catalog)
[[ $(jq -r '.schemaVersion' <<<"$catalog") == 1 ]] || fail "tool catalog keeps schema 1"
[[ $(jq -r '[.tools[] | select(.supported == true)] | map(.id) | join(",")' <<<"$catalog") == "bitwarden,codex,claude,hermes,hermes-desktop,chatgpt-desktop,memory-builtin,honcho,hindsight,mcp" ]] ||
  fail "tool catalog exposes runtime and desktop adapters"
[[ $(jq -r '[.tools[] | select(.desktop == true)] | map(.id) | join(",")' <<<"$catalog") == "hermes-desktop,chatgpt-desktop" ]] ||
  fail "desktop catalog entries are explicit"
[[ $(jq -r '[.tools[] | select(.setupOnly == true and .userConfirmable == true)] | map(.id) | join(",")' <<<"$catalog") == "honcho,hindsight,mcp" ]] ||
  fail "guided integrations remain user-confirmable"
pass "tool catalog keeps schema 1 and adds desktop adapters"

for tool in codex claude hermes; do
  : >"$log_file"
  run_tool install "$tool"
  assert_last_call "omarchy-launch-floating-terminal-with-presentation <omarchy-agent-install> <$tool>" "$tool install does not use the shared visible installer"
done
for desktop in hermes-desktop chatgpt-desktop; do
  : >"$log_file"
  run_tool install "$desktop"
  installer=omarchy-install-ai-hermes
  [[ $desktop == "chatgpt-desktop" ]] && installer=omarchy-install-ai-chatgpt
  assert_last_call "omarchy-launch-floating-terminal-with-presentation <$installer>" "$desktop does not use its existing installer"
done
if rg -q 'omarchy-pkg-drop|pacman[[:space:]]+-R|remove_tool' "$ROOT/bin/omarchy-setup-ai-tool"; then
  fail "adapter contains a removal path"
fi
pass "install actions stay visible and never add a cancellable package worker"

: >"$log_file"
run_tool open codex
assert_last_call "omarchy-launch-floating-terminal-with-presentation <codex> <login>" "Codex compatibility open does not launch official login"
: >"$log_file"
run_tool open claude
assert_last_call "omarchy-launch-floating-terminal-with-presentation <claude> <auth> <login>" "Claude compatibility open does not launch official login"
for tool in codex claude hermes; do
  : >"$log_file"
  run_tool launch "$tool"
  assert_last_call "omarchy-launch-floating-terminal-with-presentation <$tool>" "$tool interactive launch adds arguments"
done
if rg -q -- '--approve-for-me|--permission-mode|--yolo|--dangerously-skip-permissions|--allow-all|agent-trust|plugin-(add|enable)' "$ROOT/bin/omarchy-setup-ai-tool"; then
  fail "adapter contains approval bypass, trust, or silent plugin behavior"
fi
pass "official sign-in and plain interactive launch remain distinct"

: >"$log_file"
TEST_PACKAGES="$available_packages" run_tool open hermes-desktop
assert_last_call "setsid <uwsm-app> <--> <$system_bin/hermes-desktop>" "Hermes Desktop does not open its packaged launcher"
: >"$log_file"
TEST_PACKAGES="$available_packages" run_tool open chatgpt-desktop
assert_last_call "setsid <uwsm-app> <--> <$system_bin/chatgpt>" "ChatGPT Desktop does not open its packaged launcher"
: >"$log_file"
TEST_PACKAGES="$available_packages" TEST_AVAILABLE_PACKAGES="none" run_tool open chatgpt-desktop
assert_last_call "setsid <uwsm-app> <--> <$system_bin/chatgpt>" "installed ChatGPT Desktop cannot open while its repository is unavailable"
pass "desktop open actions use existing launchers"

: >"$log_file"
run_tool open memory-builtin
assert_last_call "omarchy-launch-floating-terminal-with-presentation <hermes> <memory> <status>" "built-in memory does not open official status"
for provider in honcho hindsight; do
  : >"$log_file"
  run_tool install "$provider"
  assert_last_call "omarchy-launch-floating-terminal-with-presentation <hermes> <memory> <setup> <$provider>" "$provider does not open the official wizard"
done
: >"$log_file"
run_tool install mcp
assert_last_call "omarchy-launch-floating-terminal-with-presentation <hermes> <mcp>" "MCP does not open Hermes' official picker"
pass "memory and MCP keep user-confirmed official wizards"

: >"$log_file"
set +e
check_output=$(run_tool check hermes)
check_status=$?
set -e
(( check_status == 2 )) || fail "shipped Hermes check does not exit unavailable" "$check_status"
[[ $(jq -c . <<<"$check_output") == '{"schemaVersion":1,"id":"hermes","operational":"unavailable","reasonCode":"check-unavailable"}' ]] ||
  fail "shipped Hermes check is not sanitized unavailable JSON" "$check_output"
[[ ! -s $log_file ]] || fail "unavailable Hermes check invokes a runtime" "$(<"$log_file")"
pass "pinned Hermes check is unavailable and never invokes Hermes"

set +e
planned_output=$(run_tool install speech 2>&1)
planned_status=$?
set -e
(( planned_status != 0 )) || fail "planned integration can be installed"
grep -qF "Planned: desktop speech setup is not available in this version." <<<"$planned_output" ||
  fail "planned integration failure is not explicit" "$planned_output"
pass "planned integrations fail closed"
