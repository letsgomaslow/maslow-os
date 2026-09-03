#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

migration="$ROOT/migrations/1788395901.sh"
test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

fake_bin="$test_tmp/bin"
limine_conf="$test_tmp/limine.conf"
calls="$test_tmp/calls"
mkdir -p "$fake_bin"

cat >"$fake_bin/sudo" <<'SH'
#!/bin/bash

printf '%s\n' "$*" >>"$MASLOW_TEST_CALLS"
"$@"
SH
chmod +x "$fake_bin/sudo"

cat >"$limine_conf" <<'CONF'
interface_branding: Maslow OS Bootloader
/+Omarchy
comment: Omarchy
comment: machine-id=test order-priority=50
  //linux
  comment: Kernel version: 7.2.2-arch1-1
CONF

PATH="$fake_bin:$PATH" MASLOW_TEST_CALLS="$calls" MASLOW_LIMINE_CONF="$limine_conf" \
  bash -euo pipefail "$migration" >/dev/null

grep -Fxq '/+Maslow OS' "$limine_conf" || fail "existing Limine entry was not renamed"
grep -Fxq 'comment: Maslow OS' "$limine_conf" || fail "existing Limine comment was not renamed"
grep -Fxq 'interface_branding: Maslow OS Bootloader' "$limine_conf" || fail "Limine global branding changed unexpectedly"
grep -Fq 'comment: Kernel version: 7.2.2-arch1-1' "$limine_conf" || fail "kernel metadata changed unexpectedly"
pass "migration renames only the existing visible OS entry"

: >"$calls"
PATH="$fake_bin:$PATH" MASLOW_TEST_CALLS="$calls" MASLOW_LIMINE_CONF="$limine_conf" \
  bash -euo pipefail "$migration" >/dev/null

[[ ! -s $calls ]] || fail "migration repeats its privileged edit after the entry is branded"
pass "Limine boot-entry branding migration is idempotent"
