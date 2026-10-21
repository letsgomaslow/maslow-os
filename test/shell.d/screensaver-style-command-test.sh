#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

# omarchy screensaver style edits ~/.config/omarchy/shell.json in a temporary
# home. omarchy-shell is mocked so the config reload never reaches a live shell.

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

mock_bin="$test_tmp/bin"
test_home="$test_tmp/home"
config="$test_home/.config/omarchy/shell.json"
mkdir -p "$mock_bin" "$test_home"

cat >"$mock_bin/omarchy-shell" <<'SH'
#!/bin/bash
printf '%s\n' "$*" >>"$OMARCHY_TEST_IPC_LOG"
printf 'ok\n'
SH
chmod +x "$mock_bin/omarchy-shell"

style() {
  HOME="$test_home" \
    OMARCHY_PATH="$ROOT" \
    OMARCHY_TEST_IPC_LOG="$test_tmp/ipc" \
    PATH="$mock_bin:$ROOT/bin:$PATH" \
    "$ROOT/bin/omarchy-screensaver-style" "$@"
}

jq -e '.screensaver.style == "maslow"' "$ROOT/config/omarchy/shell.json" >/dev/null ||
  fail "default shell.json uses the Maslow screensaver"
pass "default shell.json uses the Maslow screensaver"

[[ $(style status) == "maslow" ]] || fail "status reads the default style without a user config"
[[ $(style) == "maslow" ]] || fail "no argument prints the style in use"
pass "status reads the default style without a user config"

style classic
jq -e '.screensaver.style == "classic" and .idle.lock == 300 and (.bar.layout.left | length) > 0' "$config" >/dev/null ||
  fail "classic is saved on top of the default config" "$(cat "$config")"
[[ $(style status) == "classic" ]] || fail "status reports the saved classic style"
grep -Fxq 'shell reloadConfig' "$test_tmp/ipc" || fail "setting a style reloads the shell config"
pass "classic is saved and the shell reloads its config"

cat >"$config" <<'JSON'
{
  "version": 1,
  "idle": { "screensaver": 60, "lock": 120 },
  "screensaver": { "style": "classic", "extra": true },
  "bar": { "position": "bottom", "layout": { "left": [], "center": [], "right": [] } },
  "plugins": [{ "id": "community.example" }]
}
JSON

style maslow
jq -e '
  .screensaver == { "style": "maslow", "extra": true } and
  .idle == { "screensaver": 60, "lock": 120 } and
  .bar.position == "bottom" and
  .plugins == [{ "id": "community.example" }]
' "$config" >/dev/null || fail "setting a style preserves the rest of the user config" "$(cat "$config")"
[[ $(style status) == "maslow" ]] || fail "status reports the saved maslow style"
pass "setting a style preserves the rest of the user config"

printf '%s\n' '{ "version": 1, "screensaver": "classic" }' >"$config"
[[ $(style status) == "maslow" ]] || fail "status treats a malformed screensaver block as the default"
style classic
jq -e '.screensaver == { "style": "classic" }' "$config" >/dev/null ||
  fail "setting a style replaces a malformed screensaver block" "$(cat "$config")"
pass "a malformed screensaver block falls back and is replaced"

before=$(cat "$config")
status=0
style sparkle >/dev/null 2>&1 || status=$?
(( status == 2 )) || fail "an unknown style exits with status 2" "status: $status"
[[ $(cat "$config") == "$before" ]] || fail "an unknown style leaves the config untouched"
pass "an unknown style is rejected without touching the config"

help=$(style --help)
[[ $help == *"maslow"* && $help == *"classic"* ]] || fail "help names both styles" "$help"
pass "help names both styles"
