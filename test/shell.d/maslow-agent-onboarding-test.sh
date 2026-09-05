#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

export HOME="$test_tmp/home"
export OMARCHY_PATH="$ROOT"
mock_bin="$test_tmp/bin"
mkdir -p "$HOME" "$mock_bin"

cat >"$mock_bin/mise" <<'SH'
#!/bin/bash
if [[ $1 == "where" ]]; then
  [[ ${MASLOW_TEST_INSTALLED:-false} == "true" ]]
else
  printf '%s\0' "$@" >"$MASLOW_TEST_MISE_LOG"
fi
SH
cat >"$mock_bin/omarchy-shell" <<'SH'
#!/bin/bash
printf '%s\0' "$@" >"$MASLOW_TEST_SHELL_LOG"
SH
cat >"$mock_bin/gum" <<'SH'
#!/bin/bash
exit 130
SH
chmod +x "$mock_bin"/*

export PATH="$mock_bin:$ROOT/bin:$PATH"
export MASLOW_TEST_MISE_LOG="$test_tmp/mise.log"
export MASLOW_TEST_SHELL_LOG="$test_tmp/shell.log"

file_mode() {
  stat -c %a "$1" 2>/dev/null || stat -f %Lp "$1"
}

state=$(omarchy-setup-ai-state open)
[[ $(jq -r '.schemaVersion' <<<"$state") == 2 ]] || fail "AI onboarding state is versioned"
[[ $(jq -r '.currentStep' <<<"$state") == 1 ]] || fail "AI onboarding starts at the welcome stage"
[[ $(jq -r '.firstDisplayedAt != null' <<<"$state") == true ]] || fail "AI onboarding records its first display"
[[ $(jq -r '.tools | keys | length' <<<"$state") == 9 ]] || fail "AI onboarding includes every initial tool"
[[ $(file_mode "$HOME/.local/state/maslow-os/onboarding.json") == 600 ]] || fail "AI onboarding state is private"
pass "AI onboarding state is versioned, resumable, and private"

catalog=$(omarchy-setup-ai-state catalog)
[[ $(jq -r '.tools | map(.id) | join(" ")' <<<"$catalog") == "bitwarden codex claude hermes memory-builtin honcho hindsight mcp speech" ]] ||
  fail "AI onboarding catalog has an unexpected tool order"
[[ $(jq -r '[.tools[] | has("adapter")] | any' <<<"$catalog") == false ]] ||
  fail "AI onboarding identity catalog duplicates adapter capabilities"
pass "AI onboarding publishes tool identities without stale capability claims"

omarchy-setup-ai-state tool-select bitwarden true
[[ $(omarchy-setup-ai-state show | jq -r '.tools.bitwarden | [.selected, .status] | @tsv') == $'true\tselected' ]] ||
  fail "AI onboarding did not persist a selected tool"
omarchy-setup-ai-state tool-status bitwarden action-required
[[ $(omarchy-setup-ai-state show | jq -r '.tools.bitwarden | [.selected, .status, (.updatedAt != null)] | @tsv') == $'true\taction-required\ttrue' ]] ||
  fail "AI onboarding did not persist card progress"
omarchy-setup-ai-state tool-status bitwarden ready
[[ $(omarchy-setup-ai-state show | jq -r '.tools.bitwarden.status') == ready ]] ||
  fail "AI onboarding did not persist user-confirmed readiness"
if omarchy-setup-ai-state tool-status unknown ready >"$test_tmp/unknown-tool.out" 2>&1; then
  fail "AI onboarding accepted an unknown tool"
fi
if omarchy-setup-ai-state tool-status codex authenticated >"$test_tmp/unknown-status.out" 2>&1; then
  fail "AI onboarding accepted an unknown status"
fi
pass "AI onboarding validates and persists per-tool card state"

omarchy-setup-ai-state select claude
[[ $(omarchy-setup-ai-state show | jq -r '.selectedAgent, .currentStep') == $'claude\n3' ]] || fail "AI onboarding persists the selected agent and stage"
[[ $(omarchy-setup-ai-state show | jq -r '.tools.claude | [.selected, .status] | @tsv') == $'true\tselected' ]] ||
  fail "legacy agent selection did not update its tool card"
omarchy-setup-ai-state defer
: >"$MASLOW_TEST_SHELL_LOG"
omarchy-setup-ai --first-login
[[ ! -s $MASLOW_TEST_SHELL_LOG ]] || fail "deferred AI onboarding does not reopen automatically"
omarchy-setup-ai
shell_args=()
while IFS= read -r -d '' arg; do
  shell_args+=("$arg")
done <"$MASLOW_TEST_SHELL_LOG"
[[ ${shell_args[*]} == "shell summon maslow.ai-setup {}" ]] || fail "public AI setup route opens the first-party panel"
pass "AI onboarding defers automatic opening but remains manually available"

for supported_tool in bitwarden codex claude hermes memory-builtin honcho hindsight mcp; do
  omarchy-setup-ai-state reset
  omarchy-setup-ai-state tool-select "$supported_tool" true
  if omarchy-setup-ai-state complete >"$test_tmp/incomplete.out" 2>&1; then
    fail "AI onboarding completed while $supported_tool was not ready"
  fi
  [[ $(omarchy-setup-ai-state show | jq -r '.completedAt == null and .deferred == false') == true ]] ||
    fail "rejected $supported_tool completion changed the onboarding outcome"
  omarchy-setup-ai-state tool-status "$supported_tool" ready
  omarchy-setup-ai-state complete
  [[ $(omarchy-setup-ai-state show | jq -r '.completedAt != null and .deferred == false') == true ]] ||
    fail "AI onboarding rejected ready $supported_tool"
done
pass "AI onboarding completion requires every selected supported tool to be ready"

omarchy-setup-ai-state reset
omarchy-setup-ai-state tool-select honcho true
omarchy-setup-ai-state tool-select hindsight true
[[ $(omarchy-setup-ai-state show | jq -r '[.tools.honcho.selected, .tools.honcho.status, .tools.hindsight.selected] | @tsv') == $'false\tnot-started\ttrue' ]] ||
  fail "selecting Hindsight did not replace Honcho"
omarchy-setup-ai-state tool-status honcho action-required
[[ $(omarchy-setup-ai-state show | jq -r '[.tools.honcho.selected, .tools.hindsight.selected, .tools.hindsight.status] | @tsv') == $'true\tfalse\tnot-started' ]] ||
  fail "Honcho progress did not replace Hindsight"
pass "AI onboarding keeps one external memory provider selected"

omarchy-setup-ai-state tool-status honcho ready
omarchy-setup-ai-state complete

omarchy-setup-ai-state complete
: >"$MASLOW_TEST_SHELL_LOG"
omarchy-setup-ai --first-login
[[ ! -s $MASLOW_TEST_SHELL_LOG ]] || fail "completed AI onboarding reopens automatically"
omarchy-setup-ai
state=$(omarchy-setup-ai-state show)
[[ $(jq -r '.currentStep' <<<"$state") == 1 ]] || fail "manual AI setup did not return to agent selection after completion"
[[ $(jq -r '.completedAt == null and .selectedAgent == null' <<<"$state") == true ]] || fail "manual AI setup kept stale completion state"
pass "manual AI setup restarts a completed flow without reopening it automatically"

printf '{"schemaVersion":1,"currentStep":3,"firstDisplayedAt":"2026-01-01T00:00:00Z","completedAt":null,"deferred":false,"selectedAgent":"hermes","legacyNote":"keep me"}\n' >"$HOME/.local/state/maslow-os/onboarding.json"
state=$(omarchy-setup-ai-state show)
[[ $(jq -r '.schemaVersion, .legacyNote, .tools.hermes.status' <<<"$state") == $'2\nkeep me\nselected' ]] ||
  fail "schema 1 onboarding state did not migrate safely"
[[ $(jq -r '.schemaVersion' "$HOME/.local/state/maslow-os/onboarding.json") == 1 ]] ||
  fail "read-only migration rewrote existing user data"
omarchy-setup-ai-state tool-select mcp true
[[ $(jq -r '.schemaVersion, .legacyNote, .tools.hermes.status, .tools.mcp.status' "$HOME/.local/state/maslow-os/onboarding.json") == $'2\nkeep me\nselected\nselected' ]] ||
  fail "schema 1 onboarding state was not preserved on its next update"
pass "schema 1 onboarding state migrates without discarding valid fields"

printf '{"schemaVersion":2,"future":true}\n' >"$HOME/.local/state/maslow-os/onboarding.json"
catalog=$(omarchy-setup-ai-state catalog)
[[ $(jq -r '.tools | length' <<<"$catalog") == 9 ]] || fail "static catalog depends on readable user state"
[[ $(<"$HOME/.local/state/maslow-os/onboarding.json") == '{"schemaVersion":2,"future":true}' ]] || fail "catalog changed an unsupported state file"
if omarchy-setup-ai-state step 2 >"$test_tmp/future.out" 2>&1; then
  fail "future onboarding state is not overwritten"
fi
[[ $(<"$HOME/.local/state/maslow-os/onboarding.json") == '{"schemaVersion":2,"future":true}' ]] || fail "future onboarding state was changed"
pass "unknown onboarding schemas are preserved and reported"

mode='codex:--approve-for-me'
omarchy-agent-trust confirm codex "$mode" --yes
trust_file="$HOME/.local/state/maslow-os/agent-trust/codex.json"
[[ $(file_mode "$trust_file") == 600 ]] || fail "agent permission state is private"
omarchy-agent-trust status codex "$mode" || fail "matching agent permission is recognized"
if omarchy-agent-trust status codex 'codex:changed-mode'; then
  fail "a changed autonomous mode reuses old permission"
fi
if omarchy-agent-trust confirm '../../outside' "$mode" --yes; then
  fail "trust management accepted a non-agent state path"
fi
pass "agent permission is private and bound to the exact launch mode"

printf '{"schemaVersion":2,"agent":"codex"}\n' >"$trust_file"
set +e
omarchy-agent-trust status codex "$mode"
status=$?
set -e
(( status == 2 )) || fail "future trust schema is not reported as needing attention"
[[ $(<"$trust_file") == '{"schemaVersion":2,"agent":"codex"}' ]] || fail "future trust state was changed"
pass "unknown trust schemas are preserved and reported"

printf '{invalid json\n' >"$trust_file"
set +e
omarchy-agent-trust status codex "$mode"
status=$?
set -e
(( status == 2 )) || fail "invalid trust state is not reported as needing attention"
[[ $(<"$trust_file") == '{invalid json' ]] || fail "invalid trust state was changed"
rm -f "$trust_file"
pass "invalid trust state is preserved and reported"

rm -f "$HOME/.config/omarchy/defaults/agent"
: >"$MASLOW_TEST_MISE_LOG"
omarchy-agent-install codex
[[ ! -e $HOME/.config/omarchy/defaults/agent ]] || fail "install-only helper selected a default"
mise_args=()
while IFS= read -r -d '' arg; do
  mise_args+=("$arg")
done <"$MASLOW_TEST_MISE_LOG"
[[ ${mise_args[*]} == "use -g codex" ]] || fail "install-only helper delegates to mise"
if omarchy-agent-default-set codex >"$test_tmp/default.out" 2>&1; then
  fail "default-only helper accepted an uninstalled agent"
fi
MASLOW_TEST_INSTALLED=true omarchy-agent-default-set codex
[[ $(<"$HOME/.config/omarchy/defaults/agent") == codex ]] || fail "default-only helper did not select an installed agent"
pass "agent installation and default selection are separate operations"

grep -Fq "alias cx='omarchy-agent --inline --agent claude'" "$ROOT/default/bash/aliases" || fail "Claude alias bypasses the trust gate"
grep -Fq "alias cy='omarchy-agent --inline --agent codex'" "$ROOT/default/bash/aliases" || fail "Codex alias bypasses the trust gate"
grep -Fq '["omarchy-setup-ai-state", "catalog"]' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not load the tool catalog"
grep -Fq '["omarchy-setup-ai-tool", "catalog"]' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not load supported adapter actions"
grep -Fq '["omarchy-setup-ai-tool", "status", statusTool]' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not verify adapter availability and installation"
grep -Fq '["omarchy-setup-ai-state", "tool-select", toolId' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not persist safe tool selection"
grep -Fq '["omarchy-setup-ai-tool", root.activeAction, root.activeTool]' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not use the onboarding adapter boundary"
grep -Fq 'entry.supported !== true' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel enables actions without explicit adapter support"
grep -Fq 'Authentication is not inspected; complete the action shown, then mark ready.' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel treats process exit as verified authentication"
grep -Fq '["omarchy-setup-ai-state", "tool-status", toolId, "ready"]' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not persist explicit readiness confirmation"
grep -Fq 'previousStatus === "not-started" || previousStatus === "selected"' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel overwrites a meaningful saved status during refresh"
grep -Fq 'canFinish ? "complete" : "defer"' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel completes before every selected supported tool is ready"
grep -Fq 'text: root.canFinish ? "Finish" : "Finish later"' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not explain an incomplete exit"
grep -Fq 'property var stateWriteQueue: []' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not queue rapid state writes"
grep -Fq 'root.startNextStateWrite()' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not serialize queued state writes"
grep -Fq 'launchTool: String(launchTool || "")' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel launches actions before their progress is saved"
grep -Fq 'if (!installSupported && !openSupported) return "Unavailable on this system"' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel labels supported unavailable tools as planned"
grep -Fq 'enabled: !root.busy && !root.closingQueued && adapterSupported && (selected || installSupported || openSupported)' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel allows planned tools to be selected"
grep -Fq 'property bool canFinish: false' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel allows completion before readiness loads"
grep -Fq 'canFinish = stateCatalogLoaded && stateLoaded && adapterCatalogLoaded && statusChecksComplete && complete' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not gate completion on every catalog and status probe"
grep -Fq 'if (closeAfterWrite === true) closingQueued = true' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel accepts navigation after a close write is queued"
grep -Fq 'root.stateWriteQueue = []' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel leaves stale writes queued after closing"
grep -Fq 'Start with Bitwarden for secure readiness, then choose Codex, Claude Code, or Hermes.' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not explain the tested starter flow"
grep -Fq 'Hermes uses this by default. No extra provider is required.' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not explain built-in memory"
grep -Fq 'Choose this or Hindsight, not both.' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not explain the single external memory choice"
grep -Fq 'MCP connections are set up separately for each agent.' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel presents MCP as a universal connection"
grep -Fq 'if (planned) return "Guided setup planned"' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not label unavailable future setup honestly"
grep -Fq 'entry.setupOnly === true' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel ignores setup-only adapter capabilities"
grep -Fq 'item.setupOnly && item.userConfirmable ? "action-required"' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel cannot confirm a completed official wizard"
grep -Fq 'otherProvider = toolId === "honcho" ? "hindsight" : "honcho"' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not reflect external-memory exclusivity immediately"
grep -Fq 'statusChecksComplete = stateCatalogLoaded && adapterCatalogLoaded && !statusChecksFailed' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel completes after a failed status probe"
grep -Fq 'text: root.statusChecksFailed ? "Retry checks" : "Check again"' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel has no retry for failed or stale status probes"
grep -Fq 'result.available === true && result.installed !== true && (!setupOnly || prerequisiteInstalled)' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel enables setup-only actions without Hermes"
grep -Fq 'if (setupOnly && !prerequisiteInstalled) return "Set up Hermes first"' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not explain the Hermes prerequisite"
grep -Fq 'item.setupOnly && !item.prerequisiteInstalled' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel can mark stale setup-only state ready without Hermes"
grep -Fq 'visible: toolCard.selected && (!setupOnly || prerequisiteInstalled) && (openSupported || userConfirmable) && toolStatus === "action-required"' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel shows Mark ready when a setup-only prerequisite is missing"
if grep -Eq 'omarchy-agent-trust|--yolo|--auto|--approve-for-me|bypass' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml"; then
  fail "AI panel includes an automatic-permission path"
fi
if grep -Fq 'stderr:' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml"; then
  fail "AI panel collects adapter stderr that could include secrets"
fi
grep -Fq 'root.focusCurrentStep()' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not focus its current step after opening"
(( $(grep -Fc 'root.focusCurrentStep()' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml") >= 3 )) ||
  fail "AI panel does not move focus when its current step changes"
if grep -Fq 'requestActivate()' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml"; then
  fail "AI panel calls an unsupported FloatingWindow focus method"
fi
pass "Maslow AI setup uses safe adapter actions and preserves keyboard focus"
