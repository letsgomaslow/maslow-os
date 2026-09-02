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
[[ $(jq -r '.schemaVersion' <<<"$state") == 1 ]] || fail "AI onboarding state is versioned"
[[ $(jq -r '.currentStep' <<<"$state") == 1 ]] || fail "AI onboarding starts at the welcome stage"
[[ $(jq -r '.firstDisplayedAt != null' <<<"$state") == true ]] || fail "AI onboarding records its first display"
[[ $(file_mode "$HOME/.local/state/maslow-os/onboarding.json") == 600 ]] || fail "AI onboarding state is private"
pass "AI onboarding state is versioned, resumable, and private"

omarchy-setup-ai-state select claude
[[ $(omarchy-setup-ai-state show | jq -r '.selectedAgent, .currentStep') == $'claude\n3' ]] || fail "AI onboarding persists the selected agent and stage"
omarchy-setup-ai-state defer
: >"$MASLOW_TEST_SHELL_LOG"
omarchy-setup-ai --first-login
[[ ! -s $MASLOW_TEST_SHELL_LOG ]] || fail "deferred AI onboarding does not reopen automatically"
omarchy-setup-ai
mapfile -d '' -t shell_args <"$MASLOW_TEST_SHELL_LOG"
[[ ${shell_args[*]} == "shell summon maslow.ai-setup {}" ]] || fail "public AI setup route opens the first-party panel"
pass "AI onboarding defers automatic opening but remains manually available"

omarchy-setup-ai-state complete
: >"$MASLOW_TEST_SHELL_LOG"
omarchy-setup-ai --first-login
[[ ! -s $MASLOW_TEST_SHELL_LOG ]] || fail "completed AI onboarding reopens automatically"
omarchy-setup-ai
state=$(omarchy-setup-ai-state show)
[[ $(jq -r '.currentStep' <<<"$state") == 1 ]] || fail "manual AI setup did not return to agent selection after completion"
[[ $(jq -r '.completedAt == null and .selectedAgent == null' <<<"$state") == true ]] || fail "manual AI setup kept stale completion state"
pass "manual AI setup restarts a completed flow without reopening it automatically"

printf '{"schemaVersion":2,"future":true}\n' >"$HOME/.local/state/maslow-os/onboarding.json"
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
mapfile -d '' -t mise_args <"$MASLOW_TEST_MISE_LOG"
[[ ${mise_args[*]} == "use -g codex" ]] || fail "install-only helper delegates to mise"
if omarchy-agent-default-set codex >"$test_tmp/default.out" 2>&1; then
  fail "default-only helper accepted an uninstalled agent"
fi
MASLOW_TEST_INSTALLED=true omarchy-agent-default-set codex
[[ $(<"$HOME/.config/omarchy/defaults/agent") == codex ]] || fail "default-only helper did not select an installed agent"
pass "agent installation and default selection are separate operations"

grep -Fq "alias cx='omarchy-agent --inline --agent claude'" "$ROOT/default/bash/aliases" || fail "Claude alias bypasses the trust gate"
grep -Fq "alias cy='omarchy-agent --inline --agent codex'" "$ROOT/default/bash/aliases" || fail "Codex alias bypasses the trust gate"
grep -Fq 'It may run commands, modify or delete files, install software' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel omits the permission disclosure"
grep -Fq 'Finish without an agent' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel omits a no-agent completion path"
grep -Fq 'root.focusCurrentStep()' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml" || fail "AI panel does not focus its current step after opening"
if grep -Fq 'requestActivate()' "$ROOT/shell/plugins/maslow-ai-setup/Panel.qml"; then
  fail "AI panel calls an unsupported FloatingWindow focus method"
fi
pass "Maslow-managed agent entry points use the shared trust gate"
