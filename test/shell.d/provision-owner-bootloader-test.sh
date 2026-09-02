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
chmod +x "$stub_bin/getent" "$stub_bin/id" "$stub_bin/chown"

username=testuser
OMARCHY_PATH="$config_root"
log_step() { :; }

PATH="$stub_bin:/usr/bin:/bin" seed_missing_user_config
grep -Fq 'bootstrap.lua' "$test_home/.config/hypr/hyprland.lua" ||
  fail "missing user config is copied from the runtime tree"
pass "first-boot setup seeds config when the image lacks /etc/skel defaults"

printf '%s\n' preserved >"$test_home/.config/hypr/hyprland.lua"
PATH="$stub_bin:/usr/bin:/bin" seed_missing_user_config
grep -Fxq preserved "$test_home/.config/hypr/hyprland.lua" ||
  fail "an existing user config is left untouched"
pass "first-boot setup preserves an existing Hyprland config"
