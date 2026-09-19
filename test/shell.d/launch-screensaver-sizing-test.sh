#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

mock_bin="$test_tmp/bin"
call_log="$test_tmp/calls"
test_home="$test_tmp/home"
mkdir -p "$mock_bin" "$test_home/.config/omarchy/branding"

cat >"$mock_bin/pgrep" <<'SH'
#!/bin/bash
exit 1
SH

cat >"$mock_bin/omarchy-toggle-enabled" <<'SH'
#!/bin/bash
exit 1
SH

cat >"$mock_bin/omarchy-hyprland-monitor-focused" <<'SH'
#!/bin/bash
printf 'DP-1\n'
SH

cat >"$mock_bin/xdg-terminal-exec" <<'SH'
#!/bin/bash
printf '%s\n' "$OMARCHY_TEST_TERMINAL"
SH

cat >"$mock_bin/socat" <<'SH'
#!/bin/bash
exit 0
SH

cat >"$mock_bin/hyprctl" <<'SH'
#!/bin/bash
if [[ $1 == "monitors" && $2 == "-j" ]]; then
  printf '%s\n' "$OMARCHY_TEST_MONITORS"
  exit 0
fi
printf '%s\n' "$*" >>"$OMARCHY_TEST_CALL_LOG"
SH

chmod +x "$mock_bin"/*

write_artwork() {
  local columns=$1 rows=$2
  : >"$test_home/.config/omarchy/branding/screensaver.txt"
  for ((row = 0; row < rows; row++)); do
    printf '%*s\n' "$columns" '' | tr ' ' 'X' >>"$test_home/.config/omarchy/branding/screensaver.txt"
  done
}

run_launcher() {
  : >"$call_log"
  HOME="$test_home" \
    PATH="$mock_bin:$PATH" \
    OMARCHY_PATH="$ROOT" \
    OMARCHY_TEST_TERMINAL="$1" \
    OMARCHY_TEST_MONITORS="$2" \
    OMARCHY_TEST_CALL_LOG="$call_log" \
    XDG_RUNTIME_DIR="$test_tmp/runtime" \
    HYPRLAND_INSTANCE_SIGNATURE=test \
    bash "$ROOT/bin/omarchy-launch-screensaver"
}

assert_font_size() {
  local expected=$1 terminal=$2 option
  case $terminal in
  Alacritty) option="--option font.size=$expected" ;;
  ghostty) option="--font-size=$expected" ;;
  foot) option="--font=JetBrainsMono\\ Nerd\\ Font:size=$expected" ;;
  kitty) option="--override font_size=$expected" ;;
  esac

  if ! grep -Fq -- "$option" "$call_log"; then
    fail "$terminal receives its $expected-point override" "calls: $(<"$call_log")"
  fi
  pass "$terminal receives its $expected-point override"
}

monitor_1280='[{"name":"DP-1","width":1280,"height":800,"scale":1,"transform":0}]'
monitor_wide='[{"name":"DP-1","width":1920,"height":1080,"scale":1,"transform":0}]'
monitor_scaled='[{"name":"DP-1","width":2560,"height":1600,"scale":2,"transform":0}]'
monitor_rotated='[{"name":"DP-1","width":800,"height":1280,"scale":1,"transform":1}]'

cp "$ROOT/logo.txt" "$test_home/.config/omarchy/branding/screensaver.txt"
[[ $(LC_ALL=C.UTF-8 wc -L <"$test_home/.config/omarchy/branding/screensaver.txt") == 100 ]] ||
  fail "approved UTF-8 artwork measures as 100 display columns"
pass "approved UTF-8 artwork measures as 100 display columns"

for terminal in Alacritty ghostty foot kitty; do
  LC_ALL=C run_launcher "$terminal" "$monitor_1280"
  assert_font_size 15 "$terminal"
done

run_launcher foot "$monitor_wide"
assert_font_size 18 foot

# The same logical monitor must produce the same size at a higher output scale.
run_launcher foot "$monitor_scaled"
assert_font_size 15 foot

# A rotated output has the same 1280x800 logical canvas after rotation.
run_launcher foot "$monitor_rotated"
assert_font_size 15 foot

write_artwork 160 9
run_launcher foot "$monitor_1280"
assert_font_size 9 foot

write_artwork 100 60
run_launcher foot "$monitor_1280"
assert_font_size 6 foot
