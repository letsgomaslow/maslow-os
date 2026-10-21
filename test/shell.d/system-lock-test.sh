#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

mock_bin="$tmpdir/bin"
call_log="$tmpdir/calls"
mkdir -p "$mock_bin"
: >"$tmpdir/hide-timeout"

for command in hyprctl pkill timeout; do
  cat >"$mock_bin/$command" <<'SH'
#!/bin/bash
printf '%s %s\n' "$(basename "$0")" "$*" >>"$CALL_LOG"
SH
done

cat >"$mock_bin/omarchy-shell" <<'SH'
#!/bin/bash
printf '%s %s\n' "$(basename "$0")" "$*" >>"$CALL_LOG"
[[ $* == "-q screensaver hide" ]] && printf '%s' "${OMARCHY_SHELL_IPC_TIMEOUT:-unset}" >"$HIDE_TIMEOUT_LOG"
exit 0
SH

cat >"$mock_bin/pgrep" <<'SH'
#!/bin/bash
exit 1
SH
chmod +x "$mock_bin"/*

PATH="$mock_bin:$PATH" CALL_LOG="$call_log" HIDE_TIMEOUT_LOG="$tmpdir/hide-timeout" "$ROOT/bin/omarchy-system-lock"
mapfile -t shutdown < <(rg '^(pkill|timeout) ' "$call_log")

[[ ${shutdown[0]} == "pkill -x ttfx" ]] ||
  fail "system lock stops ttfx before closing its terminal" "calls: ${shutdown[*]}"
[[ ${shutdown[1]} == "timeout 1s pidwait -x ttfx" ]] ||
  fail "system lock waits for ttfx to exit" "calls: ${shutdown[*]}"
[[ ${shutdown[2]} == "pkill -f [o]rg.omarchy.screensaver" ]] ||
  fail "system lock closes the screensaver terminal after ttfx exits" "calls: ${shutdown[*]}"
pass "system lock waits for ttfx before closing its terminal"

mapfile -t shell_calls < <(rg '^omarchy-shell ' "$call_log")
[[ ${shell_calls[0]} == "omarchy-shell lock lock" ]] ||
  fail "system lock asks the shell to lock first" "calls: ${shell_calls[*]}"
[[ ${shell_calls[-1]} == "omarchy-shell -q screensaver hide" ]] ||
  fail "system lock closes the native screensaver after locking" "calls: ${shell_calls[*]}"
[[ $(<"$tmpdir/hide-timeout") == "1s" ]] ||
  fail "system lock bounds the native screensaver hide call" "timeout: $(<"$tmpdir/hide-timeout")"
pass "system lock closes the native screensaver quietly and briefly after locking"
