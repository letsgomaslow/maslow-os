#!/bin/bash

set -euo pipefail

source "$(dirname "$0")/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

test_root="$test_tmp/omarchy"
test_home="$test_tmp/home"
stub_bin="$test_tmp/bin"
mkdir -p "$test_root/migrations" "$test_home" "$stub_bin"

cat >"$stub_bin/omarchy-notification-dismiss" <<'SH'
#!/bin/bash
printf '%s\n' "$1" >>"$TEST_DISMISSALS"
SH
chmod +x "$stub_bin/omarchy-notification-dismiss"

cat >"$stub_bin/omarchy-i18n" <<'SH'
#!/bin/bash
[[ $1 == "migrate.pending" ]] || exit 1
printf '%s\n' "${TEST_MIGRATION_TITLE:-Pending Maslow OS Migrations}"
SH
chmod +x "$stub_bin/omarchy-i18n"

cat >"$test_root/migrations/100-migration.sh" <<'SH'
echo migration >>"$TEST_CALLS"
SH

run_migrate() {
  HOME="$test_home" \
  OMARCHY_PATH="$test_root" \
  PATH="$stub_bin:$ROOT/bin:$PATH" \
  TEST_CALLS="$test_tmp/calls" \
  TEST_DISMISSALS="$test_tmp/dismissals" \
    "$ROOT/bin/omarchy-migrate" "$@"
}

: >"$test_tmp/calls"
run_migrate >"$test_tmp/migrate.out"
[[ $(sed -n '1p' "$test_tmp/calls") == "migration" ]] || fail "omarchy-migrate runs pending migrations"
pass "omarchy-migrate runs migrations without force"

grep -Fx 'Pending Maslow OS Migrations' "$test_tmp/dismissals" >/dev/null || fail "omarchy-migrate dismisses current migration notifications"
grep -Fx 'Omarchy Migrations' "$test_tmp/dismissals" >/dev/null || fail "omarchy-migrate dismisses legacy migration notifications"
pass "omarchy-migrate clears current and legacy completed migration notifications"

: >"$test_tmp/dismissals"
TEST_MIGRATION_TITLE="Migrations Omarchy en attente" run_migrate >"$test_tmp/localized.out"
grep -Fx 'Migrations Omarchy en attente' "$test_tmp/dismissals" >/dev/null || fail "omarchy-migrate dismisses the localized title as one argument"
grep -Fx 'Omarchy Migrations' "$test_tmp/dismissals" >/dev/null || fail "localized cleanup retains the legacy title"
[[ $(wc -l <"$test_tmp/calls") == 1 ]] || fail "idempotent migration cleanup reruns no completed migrations"
pass "omarchy-migrate clears localized notifications on an idempotent run"

rm -rf "$test_home/.local/state/omarchy/migrations"
run_migrate --pending >"$test_tmp/pending.out"
grep -q '^100-migration\.sh$' "$test_tmp/pending.out" || fail "omarchy-migrate --pending lists pending migrations"
pass "omarchy-migrate --pending lists pending migrations"

run_migrate >"$test_tmp/migrate-second.out"
if run_migrate --pending >"$test_tmp/not-pending.out"; then
  fail "omarchy-migrate --pending exits non-zero without pending migrations"
fi
[[ ! -s $test_tmp/not-pending.out ]] || fail "omarchy-migrate --pending stays quiet without pending migrations"
pass "omarchy-migrate --pending reports no pending migrations"

if run_migrate --force >"$test_tmp/force.out" 2>&1; then
  fail "omarchy-migrate rejects obsolete --force option"
fi
grep -q 'Unknown option: --force' "$test_tmp/force.out" || fail "omarchy-migrate reports obsolete --force option"
pass "omarchy-migrate no longer needs --force"

cat >"$test_root/migrations/200-failure.sh" <<'SH'
exit 7
SH
: >"$test_tmp/dismissals"
if run_migrate >"$test_tmp/failure.out" 2>&1; then
  fail "omarchy-migrate propagates migration failure"
else
  [[ $? == 7 ]] || fail "omarchy-migrate preserves the failing migration exit code"
fi
[[ ! -s $test_tmp/dismissals ]] || fail "failed migrations retain their pending notifications"
[[ ! -e $test_home/.local/state/omarchy/migrations/200-failure.sh ]] || fail "failed migration receives no completion marker"
pass "omarchy-migrate retains notifications and pending state after failure"
