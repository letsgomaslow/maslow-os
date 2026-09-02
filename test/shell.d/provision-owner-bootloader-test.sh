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
