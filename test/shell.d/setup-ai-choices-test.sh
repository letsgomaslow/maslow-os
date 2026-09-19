#!/bin/bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/base-test.sh"
require_command jq
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
export HOME="$scratch" OMARCHY_PATH="$ROOT"
state_cmd="$ROOT/bin/omarchy-setup-ai-state"
"$state_cmd" open >/dev/null
state_file="$HOME/.local/state/maslow-os/onboarding.json"
jq '.future = {keep: true} | .setupChoices = {futureChoice: "keep"} | .tools.codex.status = "ready"' "$state_file" >"$scratch/state"
mv "$scratch/state" "$state_file"
"$state_cmd" choice account claude
"$state_cmd" choice hermes deferred
"$state_cmd" choice memory builtin
"$state_cmd" choice desktop none
jq -e '.schemaVersion == 2 and .future.keep and .setupChoices.futureChoice == "keep" and .setupChoices.account == "claude" and .tools.codex.status == "ready"' "$state_file" >/dev/null || fail "choices preserve schema, unknown fields, and historical progress"
cp "$state_file" "$scratch/before"
for invalid in 'account hermes' 'hermes verified' 'memory arbitrary' 'desktop unknown' 'personalContext secret'; do
  read -r key value <<<"$invalid"
  if "$state_cmd" choice "$key" "$value" >/dev/null 2>&1; then fail "unsupported choice accepted"; fi
  cmp "$scratch/before" "$state_file" || fail "invalid choice changed state"
done
pass "resume choices allow only setup preferences and preserve historical progress"
"$state_cmd" defer
"$state_cmd" choice desktop hermes-desktop
jq -e '.deferred == true and .completedAt == null' "$state_file" >/dev/null || fail "choice changed lifecycle"
"$state_cmd" reset
jq -e '.future.keep and .setupChoices.futureChoice == "keep" and (.setupChoices | has("account") | not) and .deferred == false' "$state_file" >/dev/null || fail "reset removed unknown data or retained current choices"
pass "choices cannot imply completion and reset preserves unknown fields"
