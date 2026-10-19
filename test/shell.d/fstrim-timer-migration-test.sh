#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

migration="$ROOT/migrations/1792410764.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

stub_bin="$test_tmp/bin"
mkdir -p "$stub_bin"
calls="$test_tmp/calls"

# Controls what the stubbed `systemctl is-enabled --quiet fstrim.timer` reports.
enabled_state="$test_tmp/enabled"

cat >"$stub_bin/systemctl" <<SH
#!/bin/bash
if [[ "\$1 \$2 \$3" == "is-enabled --quiet fstrim.timer" ]]; then
  [[ -e "$enabled_state" ]] && exit 0 || exit 1
fi
printf '%s' "\$*" >>"$calls"
printf '\n' >>"$calls"
if [[ "\$1 \$2" == "enable --now" ]]; then
  : >"$enabled_state"
fi
exit 0
SH
chmod +x "$stub_bin/systemctl"

cat >"$stub_bin/sudo" <<SH
#!/bin/bash
printf 'sudo %s' "\$*" >>"$calls"
printf '\n' >>"$calls"
"\$@"
SH
chmod +x "$stub_bin/sudo"

run_migration() {
  : >"$calls"
  PATH="$stub_bin:$PATH" bash -euo pipefail "$migration"
}

rm -f "$enabled_state"
run_migration
grep -q 'sudo systemctl enable --now fstrim.timer' "$calls" ||
  fail "the migration enables fstrim.timer when it is disabled" "$(cat "$calls")"
pass "the migration enables fstrim.timer when it is disabled"

run_migration
[[ ! -s $calls ]] || fail "the migration is idempotent once fstrim.timer is enabled" "$(cat "$calls")"
pass "the migration is idempotent once fstrim.timer is enabled"
