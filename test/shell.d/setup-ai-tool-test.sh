#!/bin/bash

source "$(dirname "$0")/base-test.sh"

require_command jq

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT

mock_bin="$tmp_dir/bin"
package_bin="$tmp_dir/package-bin"
shadow_bin="$tmp_dir/shadow-bin"
mkdir -p "$mock_bin" "$package_bin" "$shadow_bin" "$tmp_dir/home" "$tmp_dir/omarchy/install/helpers"
log_file="$tmp_dir/commands.log"
touch "$log_file"

cp "$ROOT/install/helpers/agent.sh" "$tmp_dir/omarchy/install/helpers/agent.sh"
cat >>"$tmp_dir/omarchy/install/helpers/agent.sh" <<'SH'
omarchy_agent_package_path() { printf '%s/%s' "${TEST_PACKAGE_BIN:-/nonexistent}" "$OMARCHY_AGENT_ID"; }
SH

make_mock() {
  local name="$1"
  cat >"$mock_bin/$name" <<'SH'
#!/bin/bash
printf '%s' "$(basename "$0")" >>"$COMMAND_LOG"
printf ' <%s>' "$@" >>"$COMMAND_LOG"
printf '\n' >>"$COMMAND_LOG"
exit "${MOCK_EXIT_CODE:-0}"
SH
  chmod +x "$mock_bin/$name"
}

for command in omarchy-pkg-present omarchy-pkg-available omarchy-install-and-launch omarchy-agent-install \
  omarchy-install-hermes-cli omarchy-launch-floating-terminal-with-presentation mise setsid uwsm-app gtk-launch; do
  make_mock "$command"
done

# The default fixture exercises the existing mise fallback. Packaged-command
# readiness has its own direct/shadow coverage below and in preinstalled-agent.
cat >"$mock_bin/omarchy-pkg-present" <<'SH'
#!/bin/bash
printf 'omarchy-pkg-present' >>"$COMMAND_LOG"
printf ' <%s>' "$@" >>"$COMMAND_LOG"
printf '\n' >>"$COMMAND_LOG"
exit "${MOCK_PKG_PRESENT_EXIT:-1}"
SH
chmod +x "$mock_bin/omarchy-pkg-present"

run_tool() {
  HOME="$tmp_dir/home" OMARCHY_PATH="$tmp_dir/omarchy" COMMAND_LOG="$log_file" \
    PATH="$mock_bin:$PATH" "$ROOT/bin/omarchy-setup-ai-tool" "$@"
}

catalog=$(run_tool catalog)
[[ $(jq -r '.schemaVersion' <<<"$catalog") == 1 ]] || fail "tool catalog has a versioned schema"
[[ $(jq -r '[.tools[] | select(.supported == true)] | map(.id) | join(",")' <<<"$catalog") == "bitwarden,codex,claude,hermes,memory-builtin,honcho,hindsight,mcp" ]] ||
  fail "tool catalog exposes the verified setup tools"
[[ $(jq -r '[.tools[] | select(.planned == true)] | map(.id) | join(",")' <<<"$catalog") == "speech" ]] ||
  fail "tool catalog leaves unverified tools planned"
[[ $(jq -r '[.tools[] | select(.setupOnly == true and .userConfirmable == true)] | map(.id) | join(",")' <<<"$catalog") == "honcho,hindsight,mcp" ]] ||
  fail "tool catalog identifies setup-only integrations"
pass "tool catalog separates supported and planned setup cards"

: >"$log_file"
status=$(run_tool status codex)
[[ $(jq -r '.installed' <<<"$status") == true ]] || fail "Codex status reports the installation probe"
[[ $(jq -r '.authentication' <<<"$status") == unknown ]] || fail "Codex status does not claim authentication"
[[ $(jq -r 'has("reasonCode")' <<<"$status") == false ]] || fail "ready Codex status reports a repair reason"
[[ $(jq -r 'has("token") or has("output") or has("credentials")' <<<"$status") == false ]] ||
  fail "tool status exposes no credential or provider-output fields"
grep -q '^mise <where> <codex>$' "$log_file" || fail "Codex status reuses the existing installation check" "$(<"$log_file")"
pass "tool status proves installation without inspecting authentication"

status=$(MOCK_EXIT_CODE=1 run_tool status codex)
[[ $(jq -r '.reasonCode' <<<"$status") == missing-core ]] || fail "missing Codex package is not identified as repairable core software"

for tool in codex claude hermes; do
  cat >"$package_bin/$tool" <<'SH'
#!/bin/bash
exit 0
SH
  chmod +x "$package_bin/$tool"
done
status=$(MOCK_PKG_PRESENT_EXIT=0 TEST_PACKAGE_BIN="$package_bin" PATH="$package_bin:$PATH" run_tool status codex)
[[ $(jq -r '.installed == true and (has("reasonCode") | not)' <<<"$status") == true ]] ||
  fail "direct packaged Codex command is not ready" "$status"

for tool in codex hermes; do
  cat >"$shadow_bin/$tool" <<'SH'
#!/bin/bash
exit 0
SH
  chmod +x "$shadow_bin/$tool"
done
status=$(MOCK_PKG_PRESENT_EXIT=0 TEST_PACKAGE_BIN="$package_bin" PATH="$shadow_bin:$package_bin:$PATH" run_tool status codex)
[[ $(jq -r '.installed == false and .reasonCode == "path-shadow"' <<<"$status") == true ]] ||
  fail "packaged Codex command override is mislabeled as missing software" "$status"
[[ $(jq -r 'has("reason") or has("path") or has("command")' <<<"$status") == false ]] ||
  fail "command override status exposes more than its safe reason code" "$status"
status=$(MOCK_PKG_PRESENT_EXIT=0 TEST_PACKAGE_BIN="$package_bin" PATH="$shadow_bin:$package_bin:$PATH" run_tool status hermes)
[[ $(jq -r '.installed == false and .reasonCode == "path-shadow"' <<<"$status") == true ]] ||
  fail "packaged Hermes command override is mislabeled as missing software" "$status"
pass "core status distinguishes direct package, missing package, and command override"

: >"$log_file"
run_tool install bitwarden
[[ $(tail -n 1 "$log_file") == "omarchy-install-and-launch <Bitwarden> <bitwarden> <bitwarden>" ]] ||
  fail "Bitwarden install reuses the existing visible install flow" "$(<"$log_file")"
if rg -q '(^|[[:space:]])bw([[:space:]]|$)|bw (login|unlock|get|export)' "$ROOT/bin/omarchy-setup-ai-tool"; then
  fail "Bitwarden adapter invokes a vault command"
fi
pass "Bitwarden remains a provider-owned vault"

for tool in codex claude hermes; do
  : >"$log_file"
  run_tool install "$tool"
  [[ $(tail -n 1 "$log_file") == "omarchy-launch-floating-terminal-with-presentation <omarchy-agent-install> <$tool>" ]] ||
    fail "$tool install does not open the shared Omarchy installer in a visible terminal" "$(<"$log_file")"
done
[[ ! -e $tmp_dir/home/.local/state/maslow-os/agent-trust ]] || fail "installation creates autonomous-mode trust state"
pass "agent installs reuse Omarchy ownership without granting permissions"
if rg -q 'omarchy-pkg-drop|pacman[[:space:]]+-R|uninstall|remove_tool' "$ROOT/bin/omarchy-setup-ai-tool"; then
  fail "deselecting onboarding tools can remove preinstalled software"
fi
pass "onboarding adapters never remove unselected software"

: >"$log_file"
run_tool open codex
[[ $(tail -n 1 "$log_file") == "omarchy-launch-floating-terminal-with-presentation <codex> <login>" ]] ||
  fail "Codex opens anything other than its login flow" "$(<"$log_file")"
: >"$log_file"
run_tool open claude
[[ $(tail -n 1 "$log_file") == "omarchy-launch-floating-terminal-with-presentation <claude> <auth> <login>" ]] ||
  fail "Claude opens anything other than its login flow" "$(<"$log_file")"
: >"$log_file"
run_tool open hermes
[[ $(tail -n 1 "$log_file") == "omarchy-launch-floating-terminal-with-presentation <hermes>" ]] ||
  fail "Hermes opens with added behavior flags" "$(<"$log_file")"
if rg -q -- '--approve-for-me|--permission-mode|--yolo|--dangerously-skip-permissions|--allow-all|agent-trust|plugin-(add|enable)' "$ROOT/bin/omarchy-setup-ai-tool"; then
  fail "safe tool adapter contains autonomous, trust, or silent plugin behavior"
fi
pass "provider setup opens without autonomous or plugin side effects"

: >"$log_file"
MOCK_PKG_PRESENT_EXIT=0 run_tool open bitwarden
[[ $(tail -n 1 "$log_file") == "setsid <uwsm-app> <--> <gtk-launch> <bitwarden>" ]] ||
  fail "Bitwarden open does not use its desktop application" "$(<"$log_file")"
pass "Bitwarden setup opens only the desktop application"

: >"$log_file"
run_tool install memory-builtin >/dev/null
grep -q '^omarchy-install-hermes-cli <--check>$' "$log_file" ||
  fail "built-in memory does not reuse Hermes readiness" "$(<"$log_file")"
: >"$log_file"
run_tool open memory-builtin
[[ $(tail -n 1 "$log_file") == "omarchy-launch-floating-terminal-with-presentation <hermes> <memory> <status>" ]] ||
  fail "built-in memory does not open the official status flow" "$(<"$log_file")"
pass "built-in memory stays active by default"

status=$(MOCK_EXIT_CODE=1 run_tool status honcho)
[[ $(jq -r '.setupOnly and .userConfirmable and (.prerequisiteInstalled == false)' <<<"$status") == true ]] ||
  fail "Honcho status does not gate setup when Hermes is missing"
pass "external memory reports a missing Hermes prerequisite"

for provider in honcho hindsight; do
  : >"$log_file"
  run_tool install "$provider"
  [[ $(tail -n 1 "$log_file") == "omarchy-launch-floating-terminal-with-presentation <hermes> <memory> <setup> <$provider>" ]] ||
    fail "$provider does not open the official provider chooser" "$(<"$log_file")"
  status=$(run_tool status "$provider")
  [[ $(jq -r '.installed' <<<"$status") == false ]] || fail "$provider setup is claimed without reading provider configuration"
  [[ $(jq -r '.prerequisiteInstalled' <<<"$status") == true ]] || fail "$provider status misses Hermes readiness"
  [[ $(jq -r '.setupOnly and .userConfirmable' <<<"$status") == true ]] || fail "$provider cannot be confirmed after its wizard"
done
pass "external memory uses Hermes single-provider setup without claiming completion"

: >"$log_file"
run_tool install mcp
[[ $(tail -n 1 "$log_file") == "omarchy-launch-floating-terminal-with-presentation <hermes> <mcp>" ]] ||
  fail "MCP does not open Hermes' official picker" "$(<"$log_file")"
status=$(run_tool status mcp)
[[ $(jq -r '.installed' <<<"$status") == false ]] || fail "MCP setup is claimed merely because Hermes is installed"
[[ $(jq -r '.prerequisiteInstalled' <<<"$status") == true ]] || fail "MCP status misses Hermes readiness"
[[ $(jq -r '.setupOnly and .userConfirmable' <<<"$status") == true ]] || fail "MCP setup cannot be manually confirmed"
pass "MCP setup stays scoped to Hermes"

set +e
planned_output=$(run_tool install speech 2>&1)
planned_status=$?
set -e
(( planned_status != 0 )) || fail "planned integration can be installed before it is supported"
grep -qF "Planned: desktop speech setup is not available in this version." <<<"$planned_output" ||
  fail "planned integration failure is not explicit" "$planned_output"
pass "unverified future integrations fail closed with a clear explanation"
