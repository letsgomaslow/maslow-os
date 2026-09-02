#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

function_body=$(sed -n '/^limine_entries_stale() {/,/^}/p' "$ROOT/bin/omarchy-provision-owner")
[[ -n $function_body ]] || fail "first-boot provisioning defines the Limine stale-entry check"
eval "$function_body"

test_esp="$test_tmp/esp"
stub_bin="$test_tmp/bin"
mkdir -p "$test_esp" "$stub_bin"
printf 'machine-id=00000000000000000000000000000000\n' >"$test_esp/limine.conf"

cat >"$stub_bin/omarchy-cmd-present" <<'STUB'
#!/bin/bash
for cmd in "$@"; do
  [[ -x ${0%/*}/$cmd ]] || exit 1
done
STUB
chmod +x "$stub_bin/omarchy-cmd-present"

esp_path() { printf '%s\n' "$test_esp"; }

if PATH="$stub_bin" limine_entries_stale; then
  fail "systemd-boot installs do not report inactive Limine entries as stale"
fi
pass "first-boot setup skips Limine refresh when limine-update is unavailable"

cat >"$stub_bin/limine-update" <<'STUB'
#!/bin/bash
exit 0
STUB
cat >"$stub_bin/cat" <<'STUB'
#!/bin/bash
if [[ $1 == /etc/machine-id ]]; then
  printf '%s\n' 11111111111111111111111111111111
else
  /bin/cat "$@"
fi
STUB
chmod +x "$stub_bin/limine-update" "$stub_bin/cat"

if ! PATH="$stub_bin:/usr/bin:/bin" limine_entries_stale; then
  fail "Limine installs still detect a stale machine-id entry"
fi
pass "first-boot setup retains stale-entry detection on Limine installs"

seed_function=$(sed -n '/^seed_missing_user_config() {/,/^}/p' "$ROOT/bin/omarchy-provision-owner")
[[ -n $seed_function ]] || fail "first-boot provisioning defines the missing-config fallback"
eval "$seed_function"

config_root="$test_tmp/source"
test_home="$test_tmp/home"
mkdir -p "$config_root/config/hypr" "$test_home" "$stub_bin"
printf '%s\n' 'dofile("bootstrap.lua")' >"$config_root/config/hypr/hyprland.lua"
printf '%s\n' 'MASLOW SCREENSAVER' >"$config_root/logo.txt"
printf '%s\n' 'MASLOW ABOUT' >"$config_root/icon.txt"

cat >"$stub_bin/getent" <<STUB
#!/bin/bash
printf '%s\n' 'testuser:x:1000:1000::${test_home}:/bin/bash'
STUB
cat >"$stub_bin/id" <<'STUB'
#!/bin/bash
printf '%s\n' testgroup
STUB
cat >"$stub_bin/chown" <<'STUB'
#!/bin/bash
exit 0
STUB
cat >"$stub_bin/install" <<'STUB'
#!/bin/bash
args=()
while (($#)); do
  case $1 in
    -d) directory=1; shift ;;
    -m|-o|-g) shift 2 ;;
    -m*|-o*|-g*) shift ;;
    *) args+=("$1"); shift ;;
  esac
done
if [[ ${directory:-0} == 1 ]]; then
  mkdir -p "${args[@]}"
else
  cp "${args[@]}"
fi
STUB
chmod +x "$stub_bin/getent" "$stub_bin/id" "$stub_bin/chown" "$stub_bin/install"

username=testuser
OMARCHY_PATH="$config_root"
log_step() { :; }

PATH="$stub_bin:/usr/bin:/bin" seed_missing_user_config
grep -Fq 'bootstrap.lua' "$test_home/.config/hypr/hyprland.lua" ||
  fail "missing user config is copied from the runtime tree"
pass "first-boot setup seeds config when the image lacks /etc/skel defaults"
grep -Fxq 'MASLOW SCREENSAVER' "$test_home/.config/omarchy/branding/screensaver.txt" ||
  fail "missing screensaver branding is copied from the runtime tree"
grep -Fxq 'MASLOW ABOUT' "$test_home/.config/omarchy/branding/about.txt" ||
  fail "missing About branding is copied from the runtime tree"
pass "first-boot setup seeds branding when the image lacks /etc/skel defaults"

printf '%s\n' preserved >"$test_home/.config/hypr/hyprland.lua"
printf '%s\n' 'CUSTOM SCREENSAVER' >"$test_home/.config/omarchy/branding/screensaver.txt"
printf '%s\n' 'CUSTOM ABOUT' >"$test_home/.config/omarchy/branding/about.txt"
PATH="$stub_bin:/usr/bin:/bin" seed_missing_user_config
grep -Fxq preserved "$test_home/.config/hypr/hyprland.lua" ||
  fail "an existing user config is left untouched"
pass "first-boot setup preserves an existing Hyprland config"
grep -Fxq 'CUSTOM SCREENSAVER' "$test_home/.config/omarchy/branding/screensaver.txt" ||
  fail "existing screensaver branding is left untouched"
grep -Fxq 'CUSTOM ABOUT' "$test_home/.config/omarchy/branding/about.txt" ||
  fail "existing About branding is left untouched"
pass "first-boot setup preserves existing user branding"
