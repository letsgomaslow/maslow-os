#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

migration="$ROOT/migrations/1789325478.sh"
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/bin" "$scratch/drop-ins"

export PATH="$scratch/bin:$ROOT/bin:$PATH"
export CALL_LOG="$scratch/calls"
export INSTALLED_PACKAGES="$scratch/packages"
export OMARCHY_KERNEL_LIMINE_CONF="$scratch/limine"
export OMARCHY_KERNEL_LIMINE_DROP_INS="$scratch/drop-ins"
export OMARCHY_KERNEL_REBUILD_MARKER="$scratch/state/1789325478"
export OMARCHY_KERNEL_MODULES_PATH="$scratch/modules"
# Transform only the fixed system path in a disposable fixture; production
# accepts no alternate module root from the environment.
source_migration=$migration
migration="$scratch/migration.sh"
sed "s|kernel_modules_path=\"/usr/lib/modules\"|kernel_modules_path=\"$OMARCHY_KERNEL_MODULES_PATH\"|" "$source_migration" > "$migration"
export KERNEL_TEST_ESP="$scratch/esp"
kernel="linux-omarchy"
boot_order='BOOT_ORDER="linux-omarchy, linux-omarchy-*, *, *fallback, Snapshots"'

# Exercise the real package helpers, including their post-install queries.
cat > "$scratch/bin/pacman" <<'SH'
#!/bin/bash
case "$1" in
  -Q) [[ $2 == -- ]] || exit 99; grep -Fxq -- "$3" "$INSTALLED_PACKAGES" ;;
  -Qql)
    [[ $2 == -- ]] || exit 99
    [[ ${KERNEL_TEST_NO_KERNEL_FILES:-0} == 0 ]] || exit 0
    if [[ $3 == linux-omarchy && ${KERNEL_TEST_META:-0} == 0 ]]; then
      printf '%s\n' "$OMARCHY_KERNEL_MODULES_PATH/direct/pkgbase"
    elif [[ $3 == "${KERNEL_TEST_REAL_ID:-linux-omarchy-bore}" && ${KERNEL_TEST_META:-0} == 1 ]]; then
      printf '%s\n' "$OMARCHY_KERNEL_MODULES_PATH/bore/pkgbase"
    elif [[ $3 == linux-omarchy-other && ${KERNEL_TEST_AMBIGUOUS:-0} == 1 ]]; then
      printf '%s\n' "$OMARCHY_KERNEL_MODULES_PATH/other/pkgbase"
    fi
    ;;
  -Qqo)
    [[ $2 == -- ]] || exit 99
    if [[ $3 == */pkgbase ]]; then
      printf '%s\n' "${KERNEL_TEST_PKGBASE_OWNER:-$(cat "$3")}"
    elif [[ -n ${KERNEL_TEST_OWNER:-} ]]; then
      printf '%s\n' "$KERNEL_TEST_OWNER"
    else
      cat "${3%/modules.builtin}/pkgbase"
    fi
    ;;
  -S)
    printf 'pacman %s\n' "$*" >> "$CALL_LOG"
    [[ ${INSTALL_FAIL:-0} == "0" ]] || exit 1
    for arg in "$@"; do
      [[ $arg == -* ]] || printf '%s\n' "$arg" >> "$INSTALLED_PACKAGES"
    done
    if [[ ${KERNEL_TEST_META:-0} == 1 ]]; then
      printf '%s\n' "${KERNEL_TEST_REAL_ID:-linux-omarchy-bore}" >> "$INSTALLED_PACKAGES"
    fi
    if [[ ${KERNEL_TEST_AMBIGUOUS:-0} == 1 ]]; then
      printf '%s\n' linux-omarchy-other >> "$INSTALLED_PACKAGES"
    fi
    ;;
  *) exit 99 ;;
esac
SH

cat > "$scratch/bin/sudo" <<'SH'
#!/bin/bash
printf 'sudo %s\n' "$*" >> "$CALL_LOG"
case "$1" in
  bash)
    [[ $# == 3 && $2 == -ec && $3 == *'source /usr/lib/limine/limine-common-functions'* ]] || exit 99
    [[ ${KERNEL_TEST_CONFIG_FAIL:-0} == 0 ]] || exit 1
    printf '%s\n%s\n' "$KERNEL_TEST_ESP" "${KERNEL_TEST_PREFIX:-omarchy}"
    ;;
  pacman | mkdir | touch | sed | tee | install | test | limine-mkinitcpio | limine-entry-tool) exec "$@" ;;
  *) exit 99 ;;
esac
SH

cat > "$scratch/bin/limine-mkinitcpio" <<'SH'
#!/bin/bash
[[ ${REBUILD_FAIL:-0} == "0" ]] || exit 1
[[ ${KERNEL_TEST_MISSING_UKI:-0} == 0 ]] || exit 0
image="$KERNEL_TEST_ESP/EFI/Linux/${KERNEL_TEST_PREFIX:-omarchy}_$1.efi"
if [[ ${KERNEL_TEST_EMPTY_UKI:-0} == 1 ]]; then
  : > "$image"
else
  printf '%s\n' 'fixture UKI' > "$image"
fi
SH

cat > "$scratch/bin/limine-entry-tool" <<'SH'
#!/bin/bash
[[ $* == "--tree" ]] || exit 99
printf '%s\n' 'Omarchy' '  linux-ptl' '  linux-omarchy-ptl-novrr-mm' '  linux-omarchy-fallback' '  Snapshots'
if [[ ${KERNEL_TEST_META:-0} == 0 ]]; then
  printf '%s\n' '  linux-omarchy-bore'
fi
if [[ ${MISSING_ENTRY:-0} == "0" ]]; then
  if [[ ${KERNEL_TEST_META:-0} == 1 ]]; then
    printf '  %s\n' "${KERNEL_TEST_TREE_ID:-${KERNEL_TEST_REAL_ID:-linux-omarchy-bore}}"
  else
    printf '  %s\n' "${KERNEL_TEST_TREE_ID:-linux-omarchy}"
  fi
fi
SH

cat > "$scratch/bin/pactree" <<'SH'
#!/bin/bash
[[ $* == '--unique --linear linux-omarchy' ]] || exit 99
[[ ${KERNEL_TEST_RESOLVE_FAIL:-0} == 0 ]] || exit 1
printf '%s\n' linux-omarchy
if [[ ${KERNEL_TEST_META:-0} == 1 ]]; then
  printf '%s\n' "${KERNEL_TEST_REAL_ID:-linux-omarchy-bore}"
fi
if [[ ${KERNEL_TEST_AMBIGUOUS:-0} == 1 ]]; then
  printf '%s\n' linux-omarchy-other
fi
SH

cat > "$scratch/bin/omarchy-state" <<'SH'
#!/bin/bash
[[ $* == "set reboot-required" ]] || exit 99
printf 'state %s\n' "$*" >> "$CALL_LOG"
SH

cat > "$scratch/bin/uname" <<'SH'
#!/bin/bash
case "$1" in
  -m) printf '%s\n' "${TEST_ARCH:-x86_64}" ;;
  -r) printf '%s\n' "${TEST_KERNEL_RELEASE:-7.2.5-arch1-1}" ;;
  *) exit 99 ;;
esac
SH

cat > "$scratch/bin/omarchy-notification-dismiss" <<'SH'
#!/bin/bash
exit 0
SH
chmod +x "$scratch/bin/"*

reset_fixture() {
  rm -rf "$OMARCHY_KERNEL_MODULES_PATH" "$KERNEL_TEST_ESP"
  mkdir -p "$OMARCHY_KERNEL_MODULES_PATH"/{direct,bore,other} "$KERNEL_TEST_ESP/EFI/Linux"
  printf '%s\n' linux-omarchy > "$OMARCHY_KERNEL_MODULES_PATH/direct/pkgbase"
  printf '%s\n' linux-omarchy-bore > "$OMARCHY_KERNEL_MODULES_PATH/bore/pkgbase"
  printf '%s\n' linux-omarchy-other > "$OMARCHY_KERNEL_MODULES_PATH/other/pkgbase"
  touch "$OMARCHY_KERNEL_MODULES_PATH/"{direct,bore,other}/modules.builtin
  : > "$CALL_LOG"
  printf '%s\n' linux-ptl linux-ptl-headers > "$INSTALLED_PACKAGES"
  rm -f "$OMARCHY_KERNEL_REBUILD_MARKER" "$OMARCHY_KERNEL_LIMINE_DROP_INS/"*
  cat > "$OMARCHY_KERNEL_LIMINE_CONF" <<'CONF'
KERNEL_CMDLINE[default]="root=UUID=keep-me rw cryptdevice=UUID=keep-me:root"
BOOT_ORDER="*, *fallback, Snapshots"
ENABLE_UKI=yes
CONF
  cp "$OMARCHY_KERNEL_LIMINE_CONF" "$scratch/original-limine"
}

run_migration() {
  bash -euo pipefail "$migration" > "$scratch/output" 2>&1
}

assert_preferred() {
  grep -Fxq "$boot_order" "$1" || fail "Omarchy kernels are preferred in $1"
}

assert_skipped() {
  [[ ! -s $CALL_LOG ]] || fail "excluded systems do not change" "$(<"$CALL_LOG")"
  cmp -s "$OMARCHY_KERNEL_LIMINE_CONF" "$scratch/original-limine" || fail "excluded systems keep their boot settings"
  [[ ! -e $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "excluded systems do not get a completion marker"
}

for old_kernel in linux linux-lts linux-zen linux-ptl linux-omarchy-ptl-novrr-mm; do
  reset_fixture
  printf '%s\n' "$old_kernel" "$old_kernel-headers" > "$INSTALLED_PACKAGES"
  run_migration
  grep -Fxq "$kernel" "$INSTALLED_PACKAGES" || fail "the generic kernel is installed"
  grep -Fxq "$kernel-headers" "$INSTALLED_PACKAGES" || fail "its headers are installed"
  grep -Fxq "$old_kernel" "$INSTALLED_PACKAGES" || fail "the previous kernel remains available"
  assert_preferred "$OMARCHY_KERNEL_LIMINE_CONF"
  pass "$old_kernel systems receive the generic Omarchy kernel and retain their recovery kernel"
done

for installed in linux-t2 $'linux-t2\nlinux\nlinux-ptl\nlinux-omarchy'; do
  reset_fixture
  printf '%s\n' "$installed" > "$INSTALLED_PACKAGES"
  run_migration
  assert_skipped
done
pass "linux-t2 systems are skipped even with other kernels installed"

reset_fixture
TEST_KERNEL_RELEASE=7.2.5-arch1-T2 run_migration
assert_skipped
pass "a running T2 kernel is excluded even if its package is no longer installed"

reset_fixture
TEST_ARCH=aarch64 run_migration
assert_skipped
pass "ARM systems cannot receive an x86_64 kernel"

reset_fixture
printf '%s\n' linux-omarchy-ptl-novrr-mm > "$INSTALLED_PACKAGES"
mkdir -p "$scratch/state" "$scratch/user-markers" "$scratch/omarchy/migrations"
export OMARCHY_PTL_REBUILD_MARKER="$scratch/state/1789095456"
export OMARCHY_MIGRATION_STATE="$scratch/user-markers"
touch "$OMARCHY_PTL_REBUILD_MARKER" "$OMARCHY_MIGRATION_STATE/1789095456.sh"
cp "$migration" "$scratch/omarchy/migrations/1789325478.sh"
pending=$(OMARCHY_PATH="$scratch/omarchy" "$ROOT/bin/omarchy-migrate" --pending)
[[ $pending == "1789325478.sh" ]] || fail "the renamed migration is pending after completing the old migration"
OMARCHY_PATH="$scratch/omarchy" "$ROOT/bin/omarchy-migrate" > "$scratch/output" 2>&1
grep -Fxq "$kernel" "$INSTALLED_PACKAGES" || fail "the old completion markers cannot skip the generic kernel"
[[ -f $OMARCHY_KERNEL_REBUILD_MARKER && -f $OMARCHY_MIGRATION_STATE/1789325478.sh ]] || fail "new machine and user completion markers are recorded"
assert_preferred "$OMARCHY_KERNEL_LIMINE_CONF"
pass "users who completed the PTL migration run the renamed migration with fresh completion markers"

reset_fixture
for name in dell-xps-panther-lake zz-dell-xps-panther-lake; do
  printf '%s\n' 'BOOT_ORDER="linux-ptl*, *fallback, Snapshots"' > "$OMARCHY_KERNEL_LIMINE_DROP_INS/$name.conf"
done
cp "$OMARCHY_KERNEL_LIMINE_CONF" "$OMARCHY_KERNEL_LIMINE_DROP_INS/omarchy-defaults.conf"
run_migration
grep -Fxq "pacman -S --noconfirm --needed -- $kernel $kernel-headers" "$CALL_LOG" || fail "both new packages are installed"
grep -Fxq linux-ptl "$INSTALLED_PACKAGES" || fail "the old kernel is kept for recovery"
grep -Fxq linux-ptl-headers "$INSTALLED_PACKAGES" || fail "the old kernel headers are kept"
assert_preferred "$OMARCHY_KERNEL_LIMINE_CONF"
diff -u <(sed '/^BOOT_ORDER=/d; /^$/d' "$scratch/original-limine") \
  <(sed '/^BOOT_ORDER=/d; /^$/d' "$OMARCHY_KERNEL_LIMINE_CONF") || fail "kernel command line and unrelated settings are preserved"
grep -Fxq "sudo limine-mkinitcpio $kernel" "$CALL_LOG" || fail "the new kernel's boot image is rebuilt"
[[ -f $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "successful completion is recorded"
grep -Fxq 'state set reboot-required' "$CALL_LOG" || fail "the updater must offer a reboot when retaining the old kernel"
pass "new packages install, the central boot order is set, and the old kernel remains available"

: > "$CALL_LOG"
run_migration
[[ ! -s $CALL_LOG ]] || fail "another user's run does not repeat the machine-wide migration"
pass "repeat runs are a no-op after successful completion"

reset_fixture
printf '%s\n' "$kernel" >> "$INSTALLED_PACKAGES"
run_migration
grep -Fxq "$kernel-headers" "$INSTALLED_PACKAGES" || fail "missing headers install when the kernel is already present"
pass "a partially installed kernel gets its missing headers"

reset_fixture
printf '%s\n' "$kernel" "$kernel-headers" >> "$INSTALLED_PACKAGES"
run_migration
! grep -q '^pacman -S' "$CALL_LOG" || fail "already installed packages are not reinstalled"
assert_preferred "$OMARCHY_KERNEL_LIMINE_CONF"
pass "existing new packages still receive the config repair and boot rebuild"

reset_fixture
if INSTALL_FAIL=1 run_migration; then
  fail "package installation failure must fail the migration"
fi
cmp -s "$OMARCHY_KERNEL_LIMINE_CONF" "$scratch/original-limine" || fail "install failure leaves the config untouched"
! grep -q 'limine-mkinitcpio' "$CALL_LOG" || fail "install failure does not rebuild"
[[ ! -e $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "install failure stays pending"
pass "package failures leave the old boot setup intact and the migration pending"

reset_fixture
if REBUILD_FAIL=1 run_migration; then
  fail "boot rebuild failure must fail the migration"
fi
[[ ! -e $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "rebuild failure stays pending"
! grep -q '^state ' "$CALL_LOG" || fail "rebuild failure must not request a reboot"
assert_preferred "$OMARCHY_KERNEL_LIMINE_CONF"
: > "$CALL_LOG"
run_migration
grep -Fxq "sudo limine-mkinitcpio $kernel" "$CALL_LOG" || fail "retry must rebuild even after config and packages are repaired"
[[ -f $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "retry records successful completion"
pass "a failed rebuild is retried even after config and package changes succeeded"

reset_fixture
if MISSING_ENTRY=1 run_migration; then
  fail "a silently skipped kernel build must fail the migration"
fi
[[ ! -e $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "a missing boot entry stays pending"
! grep -q '^state ' "$CALL_LOG" || fail "a missing boot entry must not request a reboot"
run_migration
[[ -f $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "a missing boot entry can be repaired on retry"
pass "older Omarchy variants and fallback entries cannot satisfy generic kernel verification"

reset_fixture
cat >> "$OMARCHY_KERNEL_LIMINE_CONF" <<'CONF'
BOOT_ORDER="linux-omarchy-*, *, *fallback, Snapshots"
  BOOT_ORDER = 'linux-lts, *, *fallback, Snapshots'
CONF
run_migration
assert_preferred "$OMARCHY_KERNEL_LIMINE_CONF"
[[ $(grep -c '^BOOT_ORDER=' "$OMARCHY_KERNEL_LIMINE_CONF") == "1" ]] || fail "only one boot order is written"
! grep -Eq '^[[:space:]]+BOOT_ORDER' "$OMARCHY_KERNEL_LIMINE_CONF" || fail "a later custom assignment cannot override first position"
pass "the exact generic kernel takes first position over previous PTL and custom orders"

reset_fixture
for name in omarchy-defaults dell-xps-panther-lake zz-dell-xps-panther-lake; do
  printf '%s\n' 'BOOT_ORDER="linux-ptl*, *fallback, Snapshots"' > "$OMARCHY_KERNEL_LIMINE_DROP_INS/$name.conf"
done
printf '%s\n' 'ENABLE_SORT=yes' >> "$OMARCHY_KERNEL_LIMINE_DROP_INS/omarchy-defaults.conf"
cp "$ROOT/etc/limine-entry-tool.d/omarchy-defaults.conf" "$OMARCHY_KERNEL_LIMINE_DROP_INS/omarchy-defaults.conf.pacnew"
run_migration
effective_order=$(bash -c 'declare -A KERNEL_CMDLINE; for conf in "$1/"*.conf "$2"; do source "$conf"; done; printf "%s" "$BOOT_ORDER"' -- "$OMARCHY_KERNEL_LIMINE_DROP_INS" "$OMARCHY_KERNEL_LIMINE_CONF")
[[ $effective_order == "linux-omarchy, linux-omarchy-*, *, *fallback, Snapshots" ]] || fail "the central config wins over old and customized drop-ins"
grep -Fxq 'ENABLE_SORT=yes' "$OMARCHY_KERNEL_LIMINE_DROP_INS/omarchy-defaults.conf" || fail "custom packaged settings survive"
cmp -s "$ROOT/etc/limine-entry-tool.d/omarchy-defaults.conf" \
  "$OMARCHY_KERNEL_LIMINE_DROP_INS/omarchy-defaults.conf.pacnew" || fail "the pacnew is left for the administrator to merge"
pass "the central boot order overrides legacy drop-ins and pacnew files without rewriting them"

reset_fixture
rm "$OMARCHY_KERNEL_LIMINE_CONF"
run_migration
assert_preferred "$OMARCHY_KERNEL_LIMINE_CONF"
pass "a missing central config is created with the exact kernel first"

# Match the official 7.2.8-8 layout: linux-omarchy is fileless and depends on
# linux-omarchy-bore, which owns both pkgbase and modules.builtin.
reset_fixture
KERNEL_TEST_META=1 run_migration
grep -Fxq 'sudo limine-mkinitcpio linux-omarchy-bore' "$CALL_LOG" || fail "the real dependency kernel is rebuilt"
grep -Fxq 'BOOT_ORDER="linux-omarchy-bore, linux-omarchy, linux-omarchy-*, *, *fallback, Snapshots"' "$OMARCHY_KERNEL_LIMINE_CONF" || fail "the resolved kernel takes first position"
[[ -s $KERNEL_TEST_ESP/EFI/Linux/omarchy_linux-omarchy-bore.efi && -f $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "the meta package needs its real kernel entry and image"
grep -Fxq linux-ptl "$INSTALLED_PACKAGES" || fail "the recovery kernel is retained for meta packages"
pass "a fileless meta package resolves to and verifies its owned dependency kernel"

for failure in KERNEL_TEST_AMBIGUOUS KERNEL_TEST_RESOLVE_FAIL; do
  reset_fixture
  if env KERNEL_TEST_META=1 "$failure=1" bash -euo pipefail "$migration" > "$scratch/output" 2>&1; then
    fail "missing or ambiguous dependency evidence must fail"
  fi
  [[ ! -e $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "failed resolution stays pending"
  ! grep -q 'limine-mkinitcpio' "$CALL_LOG" || fail "failed resolution does not rebuild an unrelated kernel"
  cmp -s "$OMARCHY_KERNEL_LIMINE_CONF" "$scratch/original-limine" || fail "failed resolution preserves boot settings"
done
pass "missing dependency evidence and multiple real kernels fail before changing boot settings"

reset_fixture
if KERNEL_TEST_META=1 KERNEL_TEST_OWNER=linux run_migration; then
  fail "an unrelated package cannot own the selected kernel modules"
fi
[[ ! -e $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "inconsistent ownership stays pending"
! grep -q 'limine-mkinitcpio' "$CALL_LOG" || fail "inconsistent ownership does not rebuild"
pass "an unrelated installed kernel cannot satisfy dependency ownership"

for missing in pkgbase modules.builtin; do
  reset_fixture
  rm "$OMARCHY_KERNEL_MODULES_PATH/bore/$missing"
  if KERNEL_TEST_META=1 run_migration; then
    fail "missing owned kernel metadata must fail"
  fi
  [[ ! -e $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "missing kernel metadata stays pending"
done
pass "missing kernel metadata or modules keeps the migration pending"

for entry in linux linux-omarchy linux-omarchy-bore-fallback linux-omarchy-other; do
  reset_fixture
  if KERNEL_TEST_META=1 KERNEL_TEST_TREE_ID="$entry" run_migration; then
    fail "only the resolved dependency's exact entry is accepted" "$entry"
  fi
  [[ ! -e $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "unrelated and fallback entries stay pending"
  ! grep -q '^state ' "$CALL_LOG" || fail "unverified entries do not request reboot"
done
pass "a meta package rejects unrelated, metadata-name and fallback boot entries"

reset_fixture
printf '%s\n' 'linux-omarchy-bore+test.1' > "$OMARCHY_KERNEL_MODULES_PATH/bore/pkgbase"
KERNEL_TEST_META=1 KERNEL_TEST_REAL_ID=linux-omarchy-bore+test.1 run_migration
[[ -f $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "valid punctuation in an exact kernel ID is accepted"
reset_fixture
printf '%s\n' 'linux-omarchy-bore+test.1' > "$OMARCHY_KERNEL_MODULES_PATH/bore/pkgbase"
if KERNEL_TEST_META=1 KERNEL_TEST_REAL_ID=linux-omarchy-bore+test.1 KERNEL_TEST_TREE_ID=linux-omarchy-boreXtestY1 run_migration; then
  fail "kernel ID punctuation cannot become regex wildcards"
fi
pass "resolved kernel names are compared literally rather than as regex patterns"

for failure in KERNEL_TEST_MISSING_UKI KERNEL_TEST_EMPTY_UKI KERNEL_TEST_CONFIG_FAIL; do
  reset_fixture
  if env KERNEL_TEST_META=1 "$failure=1" bash -euo pipefail "$migration" > "$scratch/output" 2>&1; then
    fail "an entry without a verified nonempty UKI must fail" "$failure"
  fi
  [[ ! -e $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "missing image proof stays pending"
  ! grep -q '^state ' "$CALL_LOG" || fail "missing image proof does not request reboot"
done
pass "missing or empty UKIs and failed boot configuration queries keep the migration pending"

reset_fixture
KERNEL_TEST_META=1 KERNEL_TEST_PREFIX=custom123 run_migration
[[ -s $KERNEL_TEST_ESP/EFI/Linux/custom123_linux-omarchy-bore.efi && -f $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "custom UKI naming is honored"
pass "resolved ESP and custom UKI prefix are used instead of a hardcoded boot path"

reset_fixture
if KERNEL_TEST_META=1 KERNEL_TEST_PKGBASE_OWNER=linux run_migration; then
  fail "pkgbase must itself be owned by the resolved dependency"
fi
[[ ! -e $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "foreign pkgbase ownership stays pending"
! grep -q 'limine-mkinitcpio' "$CALL_LOG" || fail "foreign pkgbase ownership does not rebuild"
pass "both pkgbase and builtin modules require consistent installed package ownership"

reset_fixture
if KERNEL_TEST_META=1 KERNEL_TEST_NO_KERNEL_FILES=1 run_migration; then
  fail "a dependency closure without a real kernel must fail"
fi
[[ ! -e $OMARCHY_KERNEL_REBUILD_MARKER ]] || fail "a fileless dependency closure stays pending"
cmp -s "$OMARCHY_KERNEL_LIMINE_CONF" "$scratch/original-limine" || fail "zero kernel resolution leaves boot settings unchanged"
pass "a dependency closure without owned kernel files cannot satisfy migration completion"
