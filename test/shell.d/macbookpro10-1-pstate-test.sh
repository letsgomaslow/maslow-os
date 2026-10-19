#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

detector="$ROOT/bin/omarchy-hw-macbookpro10-1"
hw_match="$ROOT/bin/omarchy-hw-match"
switch_script="$ROOT/bin/omarchy-hw-macbookpro10-1-pstate-switch"
rule_file="$ROOT/default/udev/macbookpro10-1-pstate.rules"
install_leaf="$ROOT/install/hardware/apple/fix-macbookpro10-1-pstate.sh"
all_sh="$ROOT/install/hardware/all.sh"
migration="$ROOT/migrations/1792349584.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

# --- Detector wiring -------------------------------------------------------

stub_bin="$test_tmp/bin"
dmi="$test_tmp/dmi"
mkdir -p "$stub_bin" "$dmi"

# The detector and omarchy-hw-match both read fixed sysfs paths. Redirect both
# into fixture files, the same technique the brcmfmac test uses, so real DMI
# content is never touched.
sed "s|/sys/class/dmi/id/sys_vendor|$dmi/sys_vendor|g" "$detector" >"$stub_bin/omarchy-hw-macbookpro10-1"
sed \
  -e "s|/sys/class/dmi/id/product_name|$dmi/product_name|g" \
  -e "s|/sys/class/dmi/id/product_family|$dmi/product_family|g" \
  "$hw_match" >"$stub_bin/omarchy-hw-match"
chmod +x "$stub_bin/omarchy-hw-macbookpro10-1" "$stub_bin/omarchy-hw-match"

run_detector() {
  PATH="$stub_bin:$PATH" "$stub_bin/omarchy-hw-macbookpro10-1"
}

printf '%s' "Apple Inc." >"$dmi/sys_vendor"
printf '%s' "MacBookPro10,1" >"$dmi/product_name"
rm -f "$dmi/product_family"
run_detector || fail "the MacBookPro10,1 detector matches the real DMI vendor and product name"
pass "the MacBookPro10,1 detector matches the real DMI vendor and product name"

printf '%s' "Apple Inc." >"$dmi/sys_vendor"
printf '%s' "MacBookPro11,1" >"$dmi/product_name"
if run_detector; then
  fail "the MacBookPro10,1 detector rejects a different MacBookPro model"
fi
pass "the MacBookPro10,1 detector rejects a different MacBookPro model"

printf '%s' "LENOVO" >"$dmi/sys_vendor"
printf '%s' "MacBookPro10,1" >"$dmi/product_name"
if run_detector; then
  fail "the MacBookPro10,1 detector requires an Apple DMI vendor"
fi
pass "the MacBookPro10,1 detector requires an Apple DMI vendor"

# --- udev rule and helper script content ------------------------------------

grep -Fq 'SUBSYSTEM=="power_supply", ATTR{type}=="Mains", ATTR{online}=="1", RUN+="/usr/share/omarchy/bin/omarchy-hw-macbookpro10-1-pstate-switch ac"' "$rule_file" ||
  fail "the udev rule forces pstate 0a through the switch helper when AC is connected"
grep -Fq 'SUBSYSTEM=="power_supply", ATTR{type}=="Mains", ATTR{online}=="0", RUN+="/usr/share/omarchy/bin/omarchy-hw-macbookpro10-1-pstate-switch battery"' "$rule_file" ||
  fail "the udev rule reverts to nouveau's default pstate through the switch helper on battery"
pass "the udev rule reacts to the real AC adapter and runs the root-owned switch helper"

# The rule's RUN+= must point at the root-owned packaged install path, never
# anything under a user's home -- that exact pattern was the privilege
# escalation migrations/1788102906.sh removed from Omarchy 3.
! grep -q '\.local/share/omarchy' "$rule_file" ||
  fail "the udev rule never points RUN+= at a user-home path"
pass "the udev rule points RUN+= only at the root-owned packaged install path"

grep -q 'omarchy-hw-macbookpro10-1 || exit 0' "$switch_script" ||
  fail "the switch helper re-checks the hardware detector as a second safety layer"
pass "the switch helper re-checks the hardware detector as a second safety layer"

# 0e and 0f carry a documented Kepler memory-reclock lockup risk and must never
# be used as an actual pstate value, though the switch helper's own comments
# are allowed to name them as the risk being deliberately avoided.
! grep -vE '^[[:space:]]*#' "$rule_file" "$switch_script" | grep -qE '\b0[ef]\b' ||
  fail "pstate 0e or 0f is never used as an actual value in the rule or the switch helper"
pass "pstate 0e and 0f are never used as an actual value"

grep -q 'apple/fix-macbookpro10-1-pstate.sh' "$all_sh" ||
  fail "the pstate udev rule install runs during hardware setup"
pass "the pstate udev rule install runs during hardware setup"

grep -q 'omarchy-hw-macbookpro10-1' "$install_leaf" ||
  fail "the install leaf is gated behind the MacBookPro10,1 detector"
pass "the install leaf is gated behind the MacBookPro10,1 detector"

# --- Switch helper behavior --------------------------------------------------

hw_true="$stub_bin/true-detector"
hw_false="$stub_bin/false-detector"
cat >"$hw_true" <<'SH'
#!/bin/bash
exit 0
SH
cat >"$hw_false" <<'SH'
#!/bin/bash
exit 1
SH
chmod +x "$hw_true" "$hw_false"

pstate_file="$test_tmp/pstate"

run_switch() {
  local detector_stub="$1" arg="$2"
  cp "$detector_stub" "$stub_bin/omarchy-hw-macbookpro10-1"
  chmod +x "$stub_bin/omarchy-hw-macbookpro10-1"
  PATH="$stub_bin:$PATH" OMARCHY_MACBOOKPRO10_1_PSTATE_PATH="$pstate_file" \
    bash -euo pipefail "$switch_script" "$arg"
}

: >"$pstate_file"
run_switch "$hw_true" ac
[[ $(<"$pstate_file") == "0a" ]] || fail "the switch helper forces pstate 0a on AC power" "$(cat "$pstate_file")"
pass "the switch helper forces pstate 0a on AC power"

: >"$pstate_file"
run_switch "$hw_true" battery
[[ $(<"$pstate_file") == "AC" ]] || fail "the switch helper reverts to nouveau's default pstate on battery" "$(cat "$pstate_file")"
pass "the switch helper reverts to nouveau's default pstate on battery"

rm -f "$pstate_file"
run_switch "$hw_false" ac
[[ ! -e $pstate_file ]] || fail "the switch helper writes nothing on non-matching hardware"
pass "the switch helper writes nothing on non-matching hardware"

# The real debugfs pstate file always exists already; only its writability is
# ever in question. Model a file that exists but cannot be written, the same
# way an unexpected permission on a real system would look.
: >"$pstate_file"
chmod 444 "$pstate_file"
run_switch "$hw_true" ac
[[ -z $(<"$pstate_file") ]] || fail "the switch helper writes nothing to an unwritable pstate file" "$(cat "$pstate_file")"
chmod 644 "$pstate_file"
pass "the switch helper writes nothing to an existing but unwritable pstate file"

PATH="$stub_bin:$PATH" OMARCHY_MACBOOKPRO10_1_PSTATE_PATH="$test_tmp/missing-debugfs/pstate" \
  bash -euo pipefail "$switch_script" ac
[[ ! -e "$test_tmp/missing-debugfs/pstate" ]] ||
  fail "the switch helper exits quietly when debugfs is not mounted"
pass "the switch helper exits quietly when the pstate path does not exist"

# --- Migration ---------------------------------------------------------------

mkdir -p "$stub_bin"
calls="$test_tmp/calls.log"

cat >"$stub_bin/sudo" <<'SH'
#!/bin/bash
printf 'sudo' >>"$TEST_LOG"
printf '\t%s' "$@" >>"$TEST_LOG"
printf '\n' >>"$TEST_LOG"
if [[ ${1:-} == "/usr/bin/udevadm" ]]; then
  exit 0
fi
"$@"
SH
chmod +x "$stub_bin/sudo"

fake_rules_dir="$test_tmp/rules.d"
fake_udev_control="$test_tmp/udev-control"
fake_omarchy_path="$test_tmp/omarchy"
mkdir -p "$fake_omarchy_path/default/udev"
cp "$rule_file" "$fake_omarchy_path/default/udev/macbookpro10-1-pstate.rules"

migration_script="$test_tmp/migration.sh"
sed \
  -e "s|^rules_dir=/etc/udev/rules.d$|rules_dir=$fake_rules_dir|" \
  -e "s|^udev_control=/run/udev/control$|udev_control=$fake_udev_control|" \
  "$migration" >"$migration_script"

run_migration() {
  local detector_stub="$1"
  cp "$detector_stub" "$stub_bin/omarchy-hw-macbookpro10-1"
  chmod +x "$stub_bin/omarchy-hw-macbookpro10-1"
  rm -rf "$fake_rules_dir"
  mkdir -p "$fake_rules_dir"
  : >"$fake_udev_control"
  : >"$calls"
  PATH="$stub_bin:$PATH" TEST_LOG="$calls" OMARCHY_PATH="$fake_omarchy_path" \
    bash -euo pipefail "$migration_script" >/dev/null
}

run_migration "$hw_true"
cmp -s "$fake_omarchy_path/default/udev/macbookpro10-1-pstate.rules" "$fake_rules_dir/90-omarchy-macbookpro10-1-pstate.rules" ||
  fail "the migration installs the packaged pstate udev rule"
grep -q $'sudo\t.*udevadm.*control.*--reload' "$calls" ||
  fail "the migration reloads udev after installing the rule" "$(cat "$calls")"
pass "the migration installs the pstate udev rule and reloads udev"

: >"$calls"
PATH="$stub_bin:$PATH" TEST_LOG="$calls" OMARCHY_PATH="$fake_omarchy_path" \
  bash -euo pipefail "$migration_script" >/dev/null
[[ ! -s $calls ]] || fail "the migration is a no-op when the rule is already installed" "$(cat "$calls")"
pass "the migration is idempotent on an already repaired machine"

run_migration "$hw_false"
[[ ! -e "$fake_rules_dir/90-omarchy-macbookpro10-1-pstate.rules" ]] ||
  fail "the migration skips a machine that is not a MacBookPro10,1"
[[ ! -s $calls ]] || fail "the migration escalates nothing on non-matching hardware" "$(cat "$calls")"
pass "the migration skips non-matching hardware without escalating"
