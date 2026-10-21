#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

# omarchy-launch-screensaver asks the shell for the native Maslow screensaver
# first and falls back to the classic terminal effects. Everything it talks to
# is mocked, so no IPC reaches a live shell and no terminal opens.

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

mock_bin="$test_tmp/bin"
call_log="$test_tmp/calls"
ipc_log="$test_tmp/ipc"
test_home="$test_tmp/home"
mkdir -p "$mock_bin" "$test_home/.config/omarchy/branding"
cp "$ROOT/logo.txt" "$test_home/.config/omarchy/branding/screensaver.txt"

cat >"$mock_bin/omarchy-shell" <<'SH'
#!/bin/bash
printf '%s\n' "$*" >>"$OMARCHY_TEST_IPC_LOG"
[[ -n $OMARCHY_TEST_SHELL_REPLY ]] && printf '%s\n' "$OMARCHY_TEST_SHELL_REPLY"
exit "$OMARCHY_TEST_SHELL_EXIT"
SH

cat >"$mock_bin/pgrep" <<'SH'
#!/bin/bash
exit 1
SH

cat >"$mock_bin/omarchy-toggle-enabled" <<'SH'
#!/bin/bash
[[ $1 == "screensaver-off" ]] && (( OMARCHY_TEST_SCREENSAVER_OFF ))
SH

cat >"$mock_bin/omarchy-hyprland-monitor-focused" <<'SH'
#!/bin/bash
printf 'DP-1\n'
SH

cat >"$mock_bin/xdg-terminal-exec" <<'SH'
#!/bin/bash
printf 'foot\n'
SH

cat >"$mock_bin/socat" <<'SH'
#!/bin/bash
exit 0
SH

cat >"$mock_bin/hyprctl" <<'SH'
#!/bin/bash
if [[ $1 == "monitors" && $2 == "-j" ]]; then
  printf '%s\n' '[{"name":"DP-1","width":1920,"height":1080,"scale":1,"transform":0}]'
  exit 0
fi
printf '%s\n' "$*" >>"$OMARCHY_TEST_CALL_LOG"
SH

chmod +x "$mock_bin"/*

launcher_status=0

# run_launcher <shell reply> <shell exit> <screensaver-off 0|1> [launcher args...]
run_launcher() {
  local reply=$1 exit_code=$2 off=$3
  shift 3
  : >"$call_log"
  : >"$ipc_log"
  launcher_status=0
  HOME="$test_home" \
    PATH="$mock_bin:$PATH" \
    OMARCHY_PATH="$ROOT" \
    OMARCHY_TEST_SHELL_REPLY="$reply" \
    OMARCHY_TEST_SHELL_EXIT="$exit_code" \
    OMARCHY_TEST_SCREENSAVER_OFF="$off" \
    OMARCHY_TEST_IPC_LOG="$ipc_log" \
    OMARCHY_TEST_CALL_LOG="$call_log" \
    XDG_RUNTIME_DIR="$test_tmp/runtime" \
    HYPRLAND_INSTANCE_SIGNATURE=test \
    bash "$ROOT/bin/omarchy-launch-screensaver" "$@" >/dev/null 2>&1 || launcher_status=$?
}

terminal_launched() {
  grep -Fq 'org.omarchy.screensaver' "$call_log"
}

asked_native() {
  grep -Fxq 'screensaver show' "$ipc_log"
}

for reply in ok locked; do
  run_launcher "$reply" 0 0
  asked_native || fail "launcher asks the shell for the native screensaver ($reply)" "ipc: $(<"$ipc_log")"
  terminal_launched && fail "native reply $reply opens no terminal" "calls: $(<"$call_log")"
  (( launcher_status == 0 )) || fail "native reply $reply exits successfully" "status: $launcher_status"
  pass "native reply $reply leaves the classic terminal closed"
done

run_launcher classic 0 0
asked_native || fail "launcher asks the shell before honoring the classic style" "ipc: $(<"$ipc_log")"
terminal_launched || fail "classic style reply opens the classic terminal" "calls: $(<"$call_log")"
pass "classic style reply opens the classic terminal"

run_launcher no-screens 0 0
terminal_launched || fail "a shell without screens falls back to the classic terminal" "calls: $(<"$call_log")"
pass "a shell without screens falls back to the classic terminal"

run_launcher "" 1 0
terminal_launched || fail "a shell that is not running falls back to the classic terminal" "calls: $(<"$call_log")"
pass "a shell that is not running falls back to the classic terminal"

# omarchy-shell reports an unknown target on stderr with exit 1; a shell build
# without the plugin must still get a screensaver.
run_launcher "Target not found." 1 0
terminal_launched || fail "a shell without the native screensaver falls back to the classic terminal" "calls: $(<"$call_log")"
pass "a shell without the native screensaver falls back to the classic terminal"

grep -Fq -- '--app-id=org.omarchy.screensaver' "$call_log" ||
  fail "classic fallback keeps the screensaver window class" "calls: $(<"$call_log")"
pass "classic fallback keeps the screensaver window class"

run_launcher ok 0 0 classic
[[ -s $ipc_log ]] && fail "the classic argument skips the native screensaver" "ipc: $(<"$ipc_log")"
terminal_launched || fail "the classic argument opens the classic terminal" "calls: $(<"$call_log")"
pass "the classic argument skips the native screensaver"

run_launcher ok 0 0 force classic
[[ -s $ipc_log ]] && fail "force classic skips the native screensaver" "ipc: $(<"$ipc_log")"
terminal_launched || fail "force classic opens the classic terminal" "calls: $(<"$call_log")"
pass "force classic skips the native screensaver"

run_launcher ok 0 1
(( launcher_status == 1 )) || fail "screensaver off stops the launcher" "status: $launcher_status"
[[ -s $ipc_log ]] && fail "screensaver off asks the shell for nothing" "ipc: $(<"$ipc_log")"
terminal_launched && fail "screensaver off opens no terminal" "calls: $(<"$call_log")"
pass "screensaver off keeps both screensaver styles closed"

run_launcher ok 0 1 force
asked_native || fail "force shows the native screensaver while it is turned off" "ipc: $(<"$ipc_log")"
terminal_launched && fail "forced native screensaver opens no terminal" "calls: $(<"$call_log")"
(( launcher_status == 0 )) || fail "forced native screensaver exits successfully" "status: $launcher_status"
pass "force shows the native screensaver while it is turned off"
