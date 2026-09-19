#!/bin/bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/base-test.sh"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/bin"
cat > "$work/bin/omarchy-cmd-present" <<'MOCK'
#!/bin/bash
exit 0
MOCK
cat > "$work/bin/omarchy-setup-ai-state" <<'MOCK'
#!/bin/bash
[[ $1 == show ]] || exit 99
printf '%s\n' "$HUB_TEST_STATE"
MOCK
cat > "$work/bin/omarchy-launch-hub" <<'MOCK'
#!/bin/bash
printf '%s %s\n' "$1" "${OMARCHY_SHELL_IPC_TIMEOUT:-default}" >> "$HUB_TEST_CALLS"
MOCK
chmod +x "$work/bin/"*
export PATH="$work/bin:$PATH" HUB_TEST_CALLS="$work/calls"
export HUB_TEST_STATE='{"completedAt":null,"deferred":false}'
bash "$ROOT/bin/omarchy-setup-ai" --first-login
grep -Fqx 'setup 60s' "$work/calls"
export HUB_TEST_STATE='{"completedAt":"2026-09-01","deferred":false}'
bash "$ROOT/bin/omarchy-setup-ai" --first-login
[[ $(wc -l < "$work/calls") == 1 ]]
bash "$ROOT/bin/omarchy-setup-ai"
grep -Fqx 'setup default' "$work/calls"
export HUB_TEST_STATE='{"completedAt":null,"deferred":true}'
bash "$ROOT/bin/omarchy-setup-ai" --first-login
[[ $(wc -l < "$work/calls") == 2 ]]
pass 'Hub routing preserves completed/deferred progress and cold-login acknowledgement'
